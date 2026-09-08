import argparse
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
import seaborn as sns

plt.style.use('seaborn-v0_8-white')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

def load_evrp_data(filepath):
    coords, demands = {}, {}
    section = None
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith('NODE_COORD_SECTION'): section = 'COORD'; continue
            elif line.startswith('DEMAND_SECTION'): section = 'DEMAND'; continue
            elif line.startswith('DEPOT_SECTION') or line == 'EOF': section = None; continue
            
            if section == 'COORD':
                parts = line.split()
                if len(parts) >= 3: coords[int(parts[0])] = (float(parts[1]), float(parts[2]))
            elif section == 'DEMAND':
                parts = line.split()
                if len(parts) >= 2: demands[int(parts[0])] = float(parts[1])
    return coords, demands

def load_route(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r') as f:
        return [int(x) for x in f.read().split() if x.strip().isdigit()]

def plot_pretty_route(ax, coords, demands, route_seq, dataset_name):
    offset = 1 if (0 in route_seq and 0 not in coords) else 0
    depot_id = 1 if offset == 1 else 0

    cust_x, cust_y, stat_x, stat_y = [], [], [], []
    depot_x, depot_y = coords[depot_id]

    for node_id, (x, y) in coords.items():
        if node_id == depot_id: continue
        if demands.get(node_id, 0) == 0:
            stat_x.append(x); stat_y.append(y)
        else:
            cust_x.append(x); cust_y.append(y)

    # Plot nodes
    ax.scatter(cust_x, cust_y, c='#a0a0a0', s=20, zorder=3, alpha=0.7, edgecolors='none', label='Customer')
    ax.scatter(stat_x, stat_y, c='#2ca02c', marker='^', s=70, zorder=4, edgecolors='black', linewidths=0.5, label='Charging Station')
    ax.scatter(depot_x, depot_y, c='#d62728', marker='s', s=120, zorder=5, edgecolors='black', linewidths=1.0, label='Depot')

    # Split routes by depot visits
    sub_routes, current_route = [], [0]
    for node in route_seq[1:]:
        current_route.append(node)
        if node == 0:
            if len(current_route) > 2: sub_routes.append(current_route)
            current_route = [0]
    if len(current_route) > 1: sub_routes.append(current_route)

    colors = sns.color_palette("tab10", n_colors=max(1, len(sub_routes)))

    for i, sub_route in enumerate(sub_routes):
        r_color = colors[i]
        for j in range(len(sub_route) - 1):
            u, v = sub_route[j] + offset, sub_route[j+1] + offset
            if u in coords and v in coords:
                x1, y1 = coords[u]
                x2, y2 = coords[v]
                ax.plot([x1, x2], [y1, y2], color=r_color, linestyle='-', linewidth=1.5, alpha=0.65, zorder=2)

    ax.set_title(f"Final Optimized EVRP Routes - {dataset_name}", fontsize=13, fontweight='bold', pad=12)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')
    ax.grid(True, linestyle=':', alpha=0.4)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dataset', type=str, required=True)
    args = parser.parse_args()
    
    dataset_name = os.path.basename(args.dataset).replace('.evrp', '').replace('.csv', '')
    target_dir = os.path.join('results', dataset_name)
    dataset_file = os.path.join('data', f"{dataset_name}.evrp")
    
    if not os.path.exists(dataset_file): return
    coords, demands = load_evrp_data(dataset_file)
    
    final_files = glob.glob(os.path.join(target_dir, f'route.{dataset_name}.evrp.txt')) + \
                  glob.glob(os.path.join(target_dir, f'route.{dataset_name}.txt'))
    
    if not final_files:
        print(f"❌ Error: Optimal route file not found.")
        return
    
    route_final = load_route(final_files[0])

    if route_final:
        fig, ax = plt.subplots(figsize=(9, 7))
        plot_pretty_route(ax, coords, demands, route_final, dataset_name)
        
        handles, labels = ax.get_legend_handles_labels()
        if handles: 
            ax.legend(handles, labels, loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize=10)
        
        plt.tight_layout()
        # Updated output filename
        plt.savefig(os.path.join(target_dir, f"route_plot_{dataset_name}.png"), dpi=300, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    main()