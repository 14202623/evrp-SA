#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits.h>
#include <math.h>
#include <random>
#include <sstream>
#include <stdio.h>
#include <stdlib.h>
#include <string>
#include <vector>
#include <sys/stat.h>
#include <sys/types.h>
#if defined(_WIN32)
#include <direct.h>
#endif

#include "EVRP.hpp"
#include "heuristic.hpp"

using namespace std;
enum OperatorID {
    OP_LOCAL_SWAP = 0,
    OP_GLOBAL_SWAP,
    OP_2OPT,
    OP_INSERT,
    OP_REMOVE,
    OP_ROUTE_MERGE
};

struct OperatorStats {
    long long calls = 0;
    long long accepted = 0;
    long long best_improvements = 0;
};

OperatorStats operator_stats[6];

extern bool termination_condition(void);
extern int MIN_VEHICLES;

vector<int> charging_station_list;
mt19937 rng_engine;

solution* best_sol;

bool use_sa = true;
bool use_repair = true;

// Hyperparameters for Simulated Annealing and Operator Probabilities
double SA_INITIAL_TEMP;
double SA_COOLING_RATE;
double P_LOCAL_SWAP;
double P_GLOBAL_SWAP;
double P_2OPT;
double P_INSERT;
double P_REMOVE;
double P_MERGE;
double P_REPAIR;

static int current_run_id = 0;
static double absolute_best_fitness = numeric_limits<double>::max();

stringstream global_log_buffer;

// Extract the base filename from a given path string
static const char* instance_basename(const char* path) {
    const char* last_slash = strrchr(path, '/');
    const char* last_backslash = strrchr(path, '\\');
    const char* base = path;

    if (last_slash != nullptr && last_slash + 1 > base) {
        base = last_slash + 1;
    }
    if (last_backslash != nullptr && last_backslash + 1 > base) {
        base = last_backslash + 1;
    }
    return base;
}

// Generate the output directory string for saving result files
string get_output_dir() {
    string base_dir = "results";
    #if defined(_WIN32)
        _mkdir(base_dir.c_str());
    #else
        mkdir(base_dir.c_str(), 0777);
    #endif

    string instance_name = instance_basename(problem_instance);
    
    size_t lastdot = instance_name.find_last_of(".");
    if (lastdot != string::npos) {
        instance_name = instance_name.substr(0, lastdot);
    }

    string out_dir = base_dir + "/" + instance_name;
    #if defined(_WIN32)
        _mkdir(out_dir.c_str());
    #else
        mkdir(out_dir.c_str(), 0777);
    #endif

    return out_dir + "/";
}

void save_route_to_file(const string& filename, const vector<int>& route) {
    string out_dir = get_output_dir();    
    string full_path = out_dir + filename;
    ofstream out(full_path);
    if (out.is_open()) {
        for (int node : route) {
            out << node << " ";
        }
        out.close();
    }
}

void set_ablation_flags(bool enable_sa, bool enable_repair) {
    use_sa = enable_sa;
    use_repair = enable_repair;
}

namespace {
    int random_index(int low, int high) {
        if (low >= high) return low;
        std::uniform_int_distribution<int> dist(low, high);
        return dist(rng_engine);
    }

    double random_real() {
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        return dist(rng_engine);
    }
}

// Load algorithm configurations from an external text file
void load_config() {
    ifstream config_file("config.txt");
    if (!config_file.is_open()) {
        cerr << "config.txt not found!" << endl;
        exit(EXIT_FAILURE);
    }
    string key;
    double value;
    while (config_file >> key >> value) {
        if (key == "SA_INITIAL_TEMP") SA_INITIAL_TEMP = value;
        else if (key == "SA_COOLING_RATE") SA_COOLING_RATE = value;
        else if (key == "P_LOCAL_SWAP") P_LOCAL_SWAP = value;
        else if (key == "P_GLOBAL_SWAP") P_GLOBAL_SWAP = value;
        else if (key == "P_2OPT") P_2OPT = value;
        else if (key == "P_INSERT") P_INSERT = value;
        else if (key == "P_REMOVE") P_REMOVE = value;
        else if (key == "P_MERGE") P_MERGE = value;
        else if (key == "P_REPAIR") P_REPAIR = value;
    }
}

double eval_energy_consumption(int from, int to) {
    return get_energy_consumption(from, to);
}

int get_nearest_charging_station(int node) {
    int sel = DEPOT;
    double sel_consumption = eval_energy_consumption(node, sel);

    for (int alt : charging_station_list) {
        double alt_consumption = eval_energy_consumption(node, alt);
        if (alt_consumption < sel_consumption) {
            sel = alt;
            sel_consumption = alt_consumption;
        }
    }
    return sel;
}

// int get_furthest_charging_station(int from, int to, double energy) {
//     int sel = get_nearest_charging_station(from);
//     double sel_consumption = eval_energy_consumption(sel, to);

//     for (int alt : charging_station_list) {
//         if (eval_energy_consumption(from, alt) <= energy) {
//             double alt_consumption = eval_energy_consumption(alt, to);
//             if (alt_consumption < sel_consumption) {
//                 sel = alt;
//                 sel_consumption = alt_consumption;
//             }
//         }
//     }
//     return sel;
// }

int get_furthest_charging_station(int from, int to, double energy) {
    int sel = get_nearest_charging_station(from);
    double best_score = numeric_limits<double>::max();

    for (int alt : charging_station_list) {
        if (eval_energy_consumption(from, alt) <= energy) {
            
            double forward_progress = eval_energy_consumption(from, alt);
            
            double remaining_dist = eval_energy_consumption(alt, to);
            
            // Score balances minimizing remaining distance and maximizing forward progress
            double score = remaining_dist - 0.6 * forward_progress;

            if (score < best_score) {
                sel = alt;
                best_score = score;
            }
        }
    }
    return sel;
}


double eval_recharge_energy_consumption(int from, int to) {
    double consumption = eval_energy_consumption(from, to);
    int recharge = get_nearest_charging_station(to);
    consumption += eval_energy_consumption(to, recharge);
    return consumption;
}

// Generate an initial random permutation of customers
vector<int> random_customer_route() {
    vector<int> route;
    for (int i = 1; i < ACTUAL_PROBLEM_SIZE; ++i) {
        if (i != DEPOT && !is_charging_station(i)) {
            route.push_back(i);
        }
    }

    std::shuffle(route.begin(), route.end(), rng_engine);
    return route;
}

// Decodes a giant tour of customers into a valid EVRP sequence
vector<int> make_valid_solution(vector<int> routes) {
    vector<int> sol;
    sol.push_back(DEPOT);
    int from = DEPOT;
    double energy = BATTERY_CAPACITY;
    double capacity = MAX_CAPACITY;

    for (int node : routes) {
        if (node == DEPOT && from == DEPOT) continue;

        double demand = get_customer_demand(node);

        // Check capacity constraint, return to depot if violated
        while (capacity < demand) {
            double consumption = eval_energy_consumption(from, DEPOT);
            while (energy < consumption) {
                int to = get_furthest_charging_station(from, DEPOT, energy);
                sol.push_back(to);
                from = to;
                energy = BATTERY_CAPACITY;
                if (to == DEPOT) capacity = MAX_CAPACITY;
                consumption = eval_energy_consumption(from, DEPOT);
            }
            if (from != DEPOT) {
                sol.push_back(DEPOT);
                from = DEPOT;
                energy = BATTERY_CAPACITY;
                capacity = MAX_CAPACITY;
            }
        }

        auto get_consumption = is_charging_station(node)
            ? function<double(int, int)>(eval_energy_consumption)
            : function<double(int, int)>(eval_recharge_energy_consumption);

        // Check energy constraint, insert charging stations if necessary
        double consumption = get_consumption(from, node);
        while (energy < consumption) {
            int to = get_furthest_charging_station(from, node, energy);
            sol.push_back(to);
            from = to;
            energy = BATTERY_CAPACITY;
            if (to == DEPOT) capacity = MAX_CAPACITY;
            consumption = get_consumption(from, node);
        }

        if (from == node) continue;

        sol.push_back(node);
        energy -= eval_energy_consumption(from, node);
        capacity -= demand;
        from = node;
    }
    
    // Ensure route properly ends at the depot
    if (from != DEPOT) {
        double consumption = eval_energy_consumption(from, DEPOT);
        while (energy < consumption) {
            int to = get_furthest_charging_station(from, DEPOT, energy);
            sol.push_back(to);
            from = to;
            energy = BATTERY_CAPACITY;
            if (to == DEPOT) {
                capacity = MAX_CAPACITY;
            }
            consumption = eval_energy_consumption(from, DEPOT);
        }
        sol.push_back(DEPOT);
    } else if (sol.empty() || sol.back() != DEPOT) {
        sol.push_back(DEPOT);
    }
    return sol;
}

// Neighborhood Operators for Local Search
vector<int> apply_local_swap(const vector<int>& seq) {
    vector<int> n = seq;
    if (n.size() < 2) return n;
    int pos = random_index(0, static_cast<int>(n.size()) - 2);
    swap(n[pos], n[pos + 1]);
    return n;
}

vector<int> apply_global_swap(const vector<int>& seq) {
    vector<int> n = seq;
    if (n.size() < 2) return n;
    int a = random_index(0, static_cast<int>(n.size()) - 1);
    int b = random_index(0, static_cast<int>(n.size()) - 1);
    while (a == b) {
        b = random_index(0, static_cast<int>(n.size()) - 1);
    }
    swap(n[a], n[b]);
    return n;
}

vector<int> apply_2opt(const vector<int>& seq) {
    vector<int> n = seq;
    if (n.size() < 2) return n;
    int a = random_index(0, static_cast<int>(n.size()) - 1);
    int b = random_index(0, static_cast<int>(n.size()) - 1);
    if (a > b) swap(a, b);
    reverse(n.begin() + a, n.begin() + b + 1);
    return n;
}

vector<int> apply_insert(const vector<int>& seq)
{
    vector<int> n = seq;

    if (n.size() <= 2)
        return n;
    int from = random_index(0, n.size() - 1);
    int customer = n[from];
    n.erase(n.begin() + from);
    int bestPos = random_index(0, n.size());
    n.insert(n.begin() + bestPos, customer);
    return n;
}

vector<int> apply_remove(const vector<int>& seq)
{
    vector<int> remain = seq;
    if (remain.size() <= 5)
        return remain;
    int remove_num=random_index(
    max(2,(int)(remain.size()*0.05)),
    max(3,(int)(remain.size()*0.15))
  );
    vector<int> removed;
    for (int i = 0; i < remove_num; i++)
    {
        int pos = random_index(0, remain.size() - 1);
        removed.push_back(remain[pos]);
        remain.erase(remain.begin() + pos);
    }

    shuffle(removed.begin(), removed.end(), rng_engine);
    for (int c : removed)
    {
        int pos = random_index(0, remain.size());
        remain.insert(remain.begin() + pos, c);
    }

    return remain;
}

// Strip out depot and charging stations to get pure customer sequence
vector<int> extract_customer_sequence(const vector<int>& route) {
    vector<int> seq;
    for (int node : route) {
        if (node == DEPOT) continue;
        if (is_charging_station(node)) continue;
        seq.push_back(node);
    }
    return seq;
}

vector<int> apply_route_merge(const vector<int>& valid_solution) {
    vector<vector<int>> routes;
    vector<int> current_route;

    for (int node : valid_solution) {
        if (node == DEPOT) {
            if (!current_route.empty()) {
                routes.push_back(current_route);
                current_route.clear();
            }
        } else if (!is_charging_station(node)) {
            current_route.push_back(node);
        }
    }
    if (routes.size() < 2) {
        return extract_customer_sequence(valid_solution);
    }
    
    int a = random_index(0, routes.size() - 1);
    int b = -1;
    double min_dist = numeric_limits<double>::max();
    bool append_b_to_a = true;

    for (int i = 0; i < static_cast<int>(routes.size()); ++i) {
        if (i == a) {
            continue;
        }
        
        double dist_a_to_b = eval_energy_consumption(routes[a].back(), routes[i].front());
        if (dist_a_to_b < min_dist) {
            min_dist = dist_a_to_b;
            b = i;
            append_b_to_a = true;
        }
        
        double dist_b_to_a = eval_energy_consumption(routes[i].back(), routes[a].front());
        if (dist_b_to_a < min_dist) {
            min_dist = dist_b_to_a;
            b = i;
            append_b_to_a = false;
        }
    }

    if (b == -1) {
        b = (a + 1) % routes.size();
        append_b_to_a = true;
    }

    vector<int> merged_customers;
    
    if (append_b_to_a) {
        merged_customers = routes[a];
        merged_customers.insert(merged_customers.end(), routes[b].begin(), routes[b].end());
    } else {
        merged_customers = routes[b];
        merged_customers.insert(merged_customers.end(), routes[a].begin(), routes[a].end());
    }

    int k = max(2, static_cast<int>(merged_customers.size() * 0.3));
    for (int i = 0; i < k; ++i) {
        int p1 = random_index(0, merged_customers.size() - 1);
        int p2 = random_index(0, merged_customers.size() - 1);
        swap(merged_customers[p1], merged_customers[p2]);
    }

    vector<int> new_flat_seq;
    
    for (int i = 0; i < static_cast<int>(routes.size()); ++i) {
        if (i == b) {
            continue;
        }
        if (i == a) {
            new_flat_seq.insert(new_flat_seq.end(), merged_customers.begin(), merged_customers.end());
        } else {
            new_flat_seq.insert(new_flat_seq.end(), routes[i].begin(), routes[i].end());
        }
    }
    return make_valid_solution(new_flat_seq);
}

void update_heuristic_solution(const vector<int>& route, double fitness) {
    int i = 0;
    for (int node : route) {
        best_sol->tour[i++] = node;
    }
    best_sol->steps = i;
    best_sol->tour_length = fitness;
}


double perform_sa_step(vector<int>& c_seq, vector<int>& current_valid_route, double& cf, double T, int& stagnation_count, string& op) {
    vector<int> n_seq;
    vector<int> candidate_route;
    
    // Roulette wheel selection for the neighborhood operator
    double p1 = P_LOCAL_SWAP;
    double p2 = p1 + P_GLOBAL_SWAP;
    double p3 = p2 + P_2OPT;
    double p4 = p3 + P_INSERT;
    double p5 = p4 + P_REMOVE;

    double r_op = random_real();
    if (r_op < p1)      { n_seq = apply_local_swap(c_seq); op = "LOCAL_SWAP"; }
    else if (r_op < p2) { n_seq = apply_global_swap(c_seq); op = "GLOBAL_SWAP"; }
    else if (r_op < p3) { n_seq = apply_2opt(c_seq); op = "2OPT"; }
    else if (r_op < p4) { n_seq = apply_insert(c_seq); op = "INSERT"; }
    else if (r_op < p5) { n_seq = apply_remove(c_seq); op = "REMOVE"; }
    else { 
        op = "ROUTE_MERGE"; 
        candidate_route = apply_route_merge(current_valid_route);
        n_seq = extract_customer_sequence(candidate_route);
    }

    if (use_repair && random_real() > P_REPAIR) {
        stagnation_count++;
        return cf;
    }

    if (op != "ROUTE_MERGE") {
        candidate_route = use_repair ? make_valid_solution(n_seq) : n_seq;
    }

    double nf = fitness_evaluation(candidate_route.data(), candidate_route.size());
    double delta = nf - cf;
    bool accepted = false;

    // Metropolis acceptance criterion
    if (!use_sa) {
        accepted = (delta < 0.0);
    } else if (delta < 0.0) {
        accepted = true;
    } else {
        double r = random_real();
        if (exp(-delta / T) > r) {
            accepted = true;
        }
    }

    // Apply the transition
    if (accepted) {
        cf = nf;
        c_seq = n_seq;
        current_valid_route = candidate_route;
    }

    // Check for global optimum update
    if (cf < best_sol->tour_length) {
        update_heuristic_solution(candidate_route, cf);
        stagnation_count = 0;
    } else {
        stagnation_count++;
    }

    return cf;
}


// Operator Statistics Tracking Module
// double perform_sa_step(vector<int>& c_seq, vector<int>& current_valid_route, double& cf, double T, int& stagnation_count, string& op, bool& accepted, bool& improved_best, double& delta) { 
//     vector<int> n_seq; 
//     vector<int> candidate_route; 
 
//     accepted = false; 
//     improved_best = false; 
//     delta = 0.0;  

//     int op_id = -1;
 
//     double p1 = P_LOCAL_SWAP; 
//     double p2 = p1 + P_GLOBAL_SWAP; 
//     double p3 = p2 + P_2OPT; 
//     double p4 = p3 + P_INSERT; 
//     double p5 = p4 + P_REMOVE; 
 
//     double r_op = random_real(); 
//     if (r_op < p1)      { n_seq = apply_local_swap(c_seq); op = "LOCAL_SWAP"; op_id = OP_LOCAL_SWAP; } 
//     else if (r_op < p2) { n_seq = apply_global_swap(c_seq); op = "GLOBAL_SWAP"; op_id = OP_GLOBAL_SWAP; } 
//     else if (r_op < p3) { n_seq = apply_2opt(c_seq); op = "2OPT"; op_id = OP_2OPT; } 
//     else if (r_op < p4) { n_seq = apply_insert(c_seq); op = "INSERT"; op_id = OP_INSERT; } 
//     else if (r_op < p5) { n_seq = apply_remove(c_seq); op = "REMOVE"; op_id = OP_REMOVE; } 
//     else {  
//         op = "ROUTE_MERGE"; op_id = OP_ROUTE_MERGE;
//         candidate_route = apply_route_merge(current_valid_route); 
//         n_seq = extract_customer_sequence(candidate_route); 
//     } 
//     if (use_repair && random_real() > P_REPAIR) { 
//         stagnation_count++; 
//         return cf; 
//     } 

//     if (op_id >= 0) {
//         operator_stats[op_id].calls++;
//     }
 
//     if (op != "ROUTE_MERGE") { 
//         candidate_route = use_repair ? make_valid_solution(n_seq) : n_seq; 
//     } 
 
//     double nf = fitness_evaluation(candidate_route.data(), candidate_route.size()); 
//     delta = nf - cf; 
 
//     if (!use_sa) { 
//         accepted = (delta < 0.0); 
//     } else if (delta < 0.0) { 
//         accepted = true; 
//     } else { 
//         double r = random_real(); 
//         if (exp(-delta / T) > r) { 
//             accepted = true; 
//         } 
//     } 
//     if (accepted) { 
//         cf = nf; 
//         c_seq = n_seq; 
//         current_valid_route = candidate_route; 
//         if (op_id >= 0) {
//             operator_stats[op_id].accepted++;
//         }
//     } 
//     if (cf < best_sol->tour_length) { 
//         update_heuristic_solution(candidate_route, cf); 
//         stagnation_count = 0; 
//         improved_best = true; 
//         if (op_id >= 0) {
//             operator_stats[op_id].best_improvements++;
//         }
//     } else { 
//         stagnation_count++; 
//     } 
 
//     return cf; 
// }

// void save_operator_statistics() {
//     static bool header_written = false;
//     string out_dir = get_output_dir(); 
//     string filepath = out_dir + "operator_statistics.csv";
//     ofstream file(filepath, ios::app);
//     if (!file.is_open()) return;

//     if (!header_written) {
//         file << "Run,Operator,Calls,Accepted,AcceptanceRate,BestImprovements\n";
//         header_written = true;
//     }

//     const string names[6] = {
//         "LOCAL_SWAP", "GLOBAL_SWAP", "2OPT", "INSERT", "REMOVE", "ROUTE_MERGE"
//     };

//     for (int i = 0; i < 6; i++) {
//         double acc_rate = (operator_stats[i].calls > 0) ? 
//             (100.0 * operator_stats[i].accepted / operator_stats[i].calls) : 0.0;

//         file << current_run_id << ","
//              << names[i] << ","
//              << operator_stats[i].calls << ","
//              << operator_stats[i].accepted << ","
//              << acc_rate << ","
//              << operator_stats[i].best_improvements << "\n";
//     }
//     file.close();
// }

// Set up the variables and initial states before execution
void initialize_heuristic(int run) {
    load_config();

    current_run_id++;

    if (best_sol != nullptr) {
        if (best_sol->tour != nullptr) {
            delete[] best_sol->tour;
        }
        delete best_sol;
        best_sol = nullptr;
    }

    best_sol = new solution;
    best_sol->tour = new int[NUM_OF_CUSTOMERS + 1000];
    best_sol->id = 1;
    best_sol->steps = 0;
    best_sol->tour_length = INT_MAX;

    charging_station_list.clear();
    for (int i = 0; i < ACTUAL_PROBLEM_SIZE; i++) {
        if (is_charging_station(i)) {
            charging_station_list.push_back(i);
        }
    }

    rng_engine = mt19937(current_run_id);

    if (current_run_id == 1) {
        global_log_buffer.str("");
        global_log_buffer.clear();
        // global_log_buffer << "RunID,Evaluations,Current_Fitness,Best_Fitness,Temperature,Operator\n";
        global_log_buffer << "RunID,Evaluations,Current_Fitness,Best_Fitness,Temperature,Operator,Accepted,Improved_Best,Delta\n";    }
}

// Main execution loop driving Simulated Annealing optimization
void run_heuristic() {
    vector<int> c_seq = random_customer_route();
    vector<int> current_valid_route = use_repair ? make_valid_solution(c_seq) : c_seq;

    double cf = fitness_evaluation(current_valid_route.data(), current_valid_route.size());
    if (cf < best_sol->tour_length) {
        update_heuristic_solution(current_valid_route, cf);
    }

    save_route_to_file("route_initial_run" + to_string(current_run_id) + ".txt", current_valid_route);

    string op = "NONE";
    double T = SA_INITIAL_TEMP;
    int stagnation_count = 0; 

    // Settings for stagnation reheating to escape local optima
    const int MAX_STAGNATION = 30000;
    const double REHEAT_RATIO = 0.15;
    const double MAX_REHEAT_TEMP = 250.0;
    
    // Milestones for saving intermediary routes
    int check_points[] = {5, 25, 50, 75, 100};
    int current_stage = 0;

    int TOTAL_EVALS = 50000; 
    
    int log_counter = 0;

    // bool accepted = false;
    // bool improved_best = false;
    // double delta = 0.0;
    // string op = "";

    while (!termination_condition()) {
        double current_cf = perform_sa_step(c_seq, current_valid_route, cf, T, stagnation_count, op);
        
        if (current_stage < 5 && get_evals() >= TOTAL_EVALS * check_points[current_stage] / 100.0) {
          vector<int> best_route_vec(best_sol->tour, best_sol->tour + best_sol->steps);
          save_route_to_file("route_" + to_string(check_points[current_stage]) + "_run" + to_string(current_run_id) + ".txt", best_route_vec);
            
          current_stage++;
        }
        if (log_counter++ % 100 == 0) {
            global_log_buffer << current_run_id << ","
                              << get_evals() << ","
                              << current_cf << ","
                              << best_sol->tour_length << ","
                              << T << ","
                              << op << "\n";
        }
        
        if (stagnation_count >= MAX_STAGNATION) {

          double target_temp = cf * REHEAT_RATIO;
          T = std::min(target_temp, MAX_REHEAT_TEMP);

          global_log_buffer << current_run_id << ","
                      << get_evals() << ","
                      << cf << ","
                      << best_sol->tour_length << ","
                      << T << ","
                      << "REHEAT\n";

          stagnation_count = 0;
        }

        if (use_sa) {
            T *= SA_COOLING_RATE;
        }
    }
}

// //Alternative Implementation: No Reheating Mechanism
// void run_heuristic() {
//     vector<int> c_seq = random_customer_route();
//     vector<int> current_valid_route = use_repair ? make_valid_solution(c_seq) : c_seq;

//     double cf = fitness_evaluation(current_valid_route.data(), current_valid_route.size());

//     if (cf < best_sol->tour_length) {
//         update_heuristic_solution(current_valid_route, cf);
//     }

//     save_route_to_file(
//         "route_initial_run" + to_string(current_run_id) + ".txt",
//         current_valid_route
//     );

//     string op = "NONE";

//     // Initial temperature
//     double T = SA_INITIAL_TEMP;

//     // Stagnation counter is no longer used for reheating.
//     int stagnation_count = 0;

//     int check_points[] = {5, 25, 50, 75, 100};
//     int current_stage = 0;

//     int TOTAL_EVALS = 50000;

//     int log_counter = 0;

//     while (!termination_condition()) {

//         double current_cf = perform_sa_step(
//             c_seq,
//             current_valid_route,
//             cf,
//             T,
//             stagnation_count,
//             op
//         );

//         // Save the best solution at different stages of the search
//         if (current_stage < 5 &&
//             get_evals() >= TOTAL_EVALS * check_points[current_stage] / 100.0) {

//             vector<int> best_route_vec(
//                 best_sol->tour,
//                 best_sol->tour + best_sol->steps
//             );

//             save_route_to_file(
//                 "route_" +
//                 to_string(check_points[current_stage]) +
//                 "_run" +
//                 to_string(current_run_id) +
//                 ".txt",
//                 best_route_vec
//             );

//             current_stage++;
//         }

//         // Logging
//         if (log_counter++ % 100 == 0) {
//             global_log_buffer << current_run_id << ","
//                               << get_evals() << ","
//                               << current_cf << ","
//                               << best_sol->tour_length << ","
//                               << T << ","
//                               << op << "\n";
//         }

//         // No reheating:
//         // the temperature follows a monotonically decreasing schedule.
//         if (use_sa) {
//             T *= SA_COOLING_RATE;
//         }
//     }
// }

//// Alternative Implementation: Operator Statistics Tracking
// void run_heuristic() { 
//     for (int i = 0; i < 6; i++) {
//         operator_stats[i] = OperatorStats();
//     }

//     vector<int> c_seq = random_customer_route(); 
//     vector<int> current_valid_route = use_repair ? make_valid_solution(c_seq) : c_seq; 
//     double cf = fitness_evaluation(current_valid_route.data(), current_valid_route.size()); 
//     if (cf < best_sol->tour_length) { 
//         update_heuristic_solution(current_valid_route, cf); 
//     } 
 
//     double T = SA_INITIAL_TEMP; 
//     int stagnation_count = 0;  
//     bool accepted = false; 
//     bool improved_best = false; 
//     double delta = 0.0; 
//     string op = "NONE"; 
 
//     const int MAX_STAGNATION = 30000; 
//     const double REHEAT_RATIO = 0.15; 
//     const double MAX_REHEAT_TEMP = 250.0; 

//     while (!termination_condition()) { 
//         cf = perform_sa_step(c_seq, current_valid_route, cf, T, stagnation_count, op, accepted, improved_best, delta); 
         
//         if (stagnation_count >= MAX_STAGNATION) { 
//             double target_temp = cf * REHEAT_RATIO; 
//             T = std::min(target_temp, MAX_REHEAT_TEMP); 
//             stagnation_count = 0; 
//         } 
 
//         if (use_sa) { 
//             T *= SA_COOLING_RATE; 
//         } 
//     } 

//     save_operator_statistics();
// }

// Clean up memory and write out the final log entries
void free_heuristic() {
    if (best_sol == nullptr) return;

    string out_dir = get_output_dir();

    if (best_sol->tour_length < absolute_best_fitness) {
        absolute_best_fitness = best_sol->tour_length;

        ofstream rf;
        string route_filename = out_dir + "route." + instance_basename(problem_instance) + ".txt";
        rf.open(route_filename.c_str(), ios::trunc);
        if (rf.is_open()) {
            for (int i = 0; i < best_sol->steps; i++) {
                rf << best_sol->tour[i] << " ";
            }
            rf.close();
        }
    }

    if (best_sol->tour != nullptr) {
        delete[] best_sol->tour;
    }
    delete best_sol;
    best_sol = nullptr;

    charging_station_list.clear();

    string log_filename = out_dir + "route_log_dynamic." + instance_basename(problem_instance) + ".csv";
    ofstream logFile(log_filename.c_str());
    if (logFile.is_open()) {
        logFile << global_log_buffer.str();
        logFile.close();
    }
}