# Electric Vehicle Routing Problem — Simulated Annealing Solver

This repository contains the C++ implementation developed for the the Electric Vehicle Routing Problem (EVRP). 

The project implements a Simulated Annealing (SA) heuristic for solving EVRP benchmark instances. The solver incorporates multiple neighbourhood operators and a feasibility repair mechanism to generate solutions satisfying the operational constraints of the EVRP. 

The repository contains the source code, configuration files, and supporting materials required to reproduce the experiments reported in the ERP report.

# Repository Structure：
The main source files are organised as follows:

    EVRP-Simulated-Annealing/
    │
    ├── EVRP.cpp
    ├── EVRP.hpp
    │
    ├── heuristic.cpp
    ├── heuristic.hpp
    │
    ├── stats.cpp
    ├── stats.hpp
    │
    ├── main.cpp
    │
    ├── makefile
    ├── config.txt
    │
    ├── plot_*.py (Visualization Scripts)
    │
    ├── data/
    │
    ├── results/
    │
    └── README.md

# EVRP.cpp EVRP.hpp
Implementation of the electric vehicle routing. 
The parameters and functions in this class can be used in the implementation of your solver

# heuristic.cpp heuristic.hpp
The heuristic search implementation. 
The original project framework provides a sample heuristic that generates solutions randomly. 
In this project, the heuristic implementation was extended to incorporate the Simulated Annealing search procedure and the neighbourhood operators used in the experiments.

# stats.cpp stats.hpp
Implementation to store the best solution for the 21 RUNS. 
The functions in this class can be used in your implementation to generate the required results of your solver in output text files。

# main.cpp
Executable of the source code。

# config.txt
Parameters used to control the heuristic and Simulated Annealing search. 
Keeping the parameters in a separate configuration file allows the experimental settings to be changed without modifying the main source code.

# Python Visualization Scripts ('plot_*.py')
Scripts developed using 'pandas' and 'matplotlib' to parse the log files, visualize the final EVRP routes, and plot the convergence trends and temperature reheating behaviors included in the ERP report.

# Dataset
The experiments use standard EVRP benchmark instances from the IEEE WCCI-2020 Evolutionary Computation Competition. The benchmark instances are publicly available. 

The dataset can be obtained from the official EVRP Competition repository:

https://mavrovouniotis.github.io/EVRPcompetition2020/

After downloading the required instances, place them in the appropriate data directory specified by the project:
    data/
        ├── E-n22-k4.evrp
        ├── E-n23-k3.evrp
        ├── ...
        └── X-n1001-k43.evrp

# Requirements
The solver is implemented in C++.
C++ compiler supporting C++11 or later is required.
Python 3.x with 'pandas', 'matplotlib', and 'seaborn' is only required if the visualisation scripts are used.

# Compilation
The project includes a 'makefile' for streamlined compilation. To compile the source code, navigate to the root directory in your terminal and run:
    make
The project can be compiled using a C++ compiler.
For the submitted implementation, the source files can be compiled using:
g++ -O3 -std=c++11 main.cpp EVRP.cpp heuristic.cpp stats.cpp -o EVRP.exe

# Configuration
The experimental parameters are specified in 'config.txt'. The final Simulated Annealing configuration used in the ERP experiments:

    SA_INITIAL_TEMP 4000.0
    SA_COOLING_RATE 0.9995
    P_LOCAL_SWAP 0.30
    P_GLOBAL_SWAP 0.25
    P_2OPT 0.15
    P_INSERT 0.10
    P_REMOVE 0.10
    P_MERGE 0.10
    P_REPAIR 1.0

# Running the Solver
After compilation, the executable can be run on an EVRP benchmark instance. For example:

    ./data/E-n33-k4.evrp

The solver generates the solution and statistical output required for the experimental analysis. For the benchmark evaluation reported in the ERP, each instance was evaluated using 21 independent runs.

# Reproducing the Experiments
The main experiments reported in the ERP can be reproduced using the following procedure:

1. Download the required EVRP benchmark instances from the official competition repository.
2. Place the instances in the required 'data/' directory.
3. Clone or download this repository.
4. Verify the parameters in 'config.txt'.
5. Compile the C++ source code using 'make'.
6. Run the solver for the selected benchmark instances.
7. Repeat each experiment for 21 independent runs.
8. Collect the resulting fitness values.
9. Use the provided Python files ('plot_*.py') to calculate the reported statistics and generate visualizations.

The main experimental analyses include:
Overall benchmark performance
Individual neighbourhood operator performance
Cooling-rate analysis
Temperature reheating analysis

The resulting statistics can be compared with the corresponding tables and figures in the ERP report.


# Additional Documentation
Further details concerning the experimental methodology, parameter settings, dataset access, and reproduction procedures are provided in the Additional Materials submitted alongside this repository.
