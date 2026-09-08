import os
import matplotlib.pyplot as plt

def parse_evrp_file(file_path):
    """
    Reads an EVRP instance file and extracts the coordinates for depots, customers, and stations.
    """
    coords = {}
    stations = set()
    depots = set()
    current_section = None

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line == 'EOF':
                continue

            if line.startswith('NODE_COORD_SECTION'):
                current_section = 'NODE_COORD'
                continue
            elif line.startswith('STATIONS_COORD_SECTION'):
                current_section = 'STATIONS'
                continue
            elif line.startswith('DEPOT_SECTION'):
                current_section = 'DEPOT'
                continue
            elif line.startswith('DEMAND_SECTION') or line.startswith('EDGE_WEIGHT_SECTION'):
                current_section = 'OTHER'
                continue

            parts = line.split()
            if not parts:
                continue

            if current_section == 'NODE_COORD':
                node_id = int(parts[0])
                coords[node_id] = (float(parts[1]), float(parts[2]))
            elif current_section == 'STATIONS':
                stations.add(int(parts[0]))
            elif current_section == 'DEPOT':
                node_id = int(parts[0])
                if node_id != -1:
                    depots.add(node_id)

    depot_coords = [coords[nid] for nid in depots if nid in coords]
    station_coords = [coords[nid] for nid in stations if nid in coords]
    customer_coords = [
        coords[nid] for nid in coords 
        if nid not in depots and nid not in stations
    ]

    return depot_coords, customer_coords, station_coords

def plot_evrp_instance(file_path, output_dir="figures"):
    """
    Parses the file, plots the instance, and automatically saves the figure.
    """
    instance_name = os.path.splitext(os.path.basename(file_path))[0]
    
    depot_coords, customer_coords, station_coords = parse_evrp_file(file_path)

    fig, ax = plt.subplots(figsize=(8, 6))

    if customer_coords:
        cx, cy = zip(*customer_coords)
        ax.scatter(cx, cy, color='blue', s=8, label='Customers', zorder=2)

    if station_coords:
        sx, sy = zip(*station_coords)
        ax.scatter(sx, sy, color='black', marker='s', s=30, label='Charging Stations', zorder=3)

    if depot_coords:
        dx, dy = zip(*depot_coords)
        ax.scatter(dx, dy, color='red', marker='o', s=40, label='Depot', zorder=4)

    ax.set_title(instance_name, fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='-', color='lightgray', alpha=0.6)
    ax.legend(loc='upper right', fontsize=10)
    
    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"{instance_name}_topology.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"[{instance_name}] Plot successfully saved to: {save_path}")

if __name__ == "__main__":
    TARGET_FILE = "data/E-n33-k4.evrp" 
    
    if os.path.exists(TARGET_FILE):
        plot_evrp_instance(TARGET_FILE)
    else:
        print(f"Error: File '{TARGET_FILE}' not found. Please check the path.")

    ""
    import glob
    
    for file_path in glob.glob("data/*.evrp"):
        plot_evrp_instance(file_path)
    ""