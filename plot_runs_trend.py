import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os

def plot_trend(log_path, cutoff_eval):
    print(f"Processing Runs Trend log: {log_path}")
    if not os.path.exists(log_path): 
        return

    # Extract instance name from filename
    base_name = os.path.basename(log_path).replace('.csv', '')
    instance_name = base_name.replace('route_log_dynamic.', '').replace('.evrp', '')

    df = pd.read_csv(log_path)
    if df.empty:
        print(f"SKIP: {log_path} is empty.")
        return

    # Establish uniform X-axis grid for alignment across all runs
    max_eval = df['Evaluations'].max()
    step_size = max(1000, int(max_eval / 1000)) 
    common_evals = np.arange(0, max_eval + step_size, step_size)

    aligned_data = []
    for run_id, group in df.groupby('RunID'):
        group = group.drop_duplicates(subset=['Evaluations'], keep='last')
        s = pd.Series(group['Best_Fitness'].values, index=group['Evaluations'])
        s_aligned = s.reindex(s.index.union(common_evals)).ffill()
        s_common = s_aligned.loc[common_evals].bfill()
        aligned_data.append(s_common.values)

    aligned_df = pd.DataFrame(aligned_data, columns=common_evals)
    summary_max = aligned_df.max(axis=0)
    summary_median = aligned_df.median(axis=0)
    summary_min = aligned_df.min(axis=0)

    # 1x2 Subplots for global and zoomed convergence views
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5))

    # Add global title including instance name
    fig.suptitle(f'Convergence Analysis - Instance: {instance_name}', fontsize=16, fontweight='bold', y=0.98)

    # Left: Full View
    ax1.plot(common_evals, summary_max, color='salmon', linestyle='--', linewidth=1.5, label='Worst Run')
    ax1.plot(common_evals, summary_median, color='indianred', linestyle='-.', linewidth=2, label='Median Run')
    ax1.plot(common_evals, summary_min, color='darkred', linestyle='-', linewidth=2, label='Best Run')
    ax1.set_title('Global Convergence Curve (Overall Drop)', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Evaluations', fontsize=12)
    ax1.set_ylabel('Fitness (Cost)', fontsize=12)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)

    # Right: Zoomed View (Refinement Phase)
    zoom_mask = common_evals > cutoff_eval
    if zoom_mask.any():
        ax2.plot(common_evals[zoom_mask], summary_max[zoom_mask], color='salmon', linestyle='--', linewidth=1.5, label='Worst Run')
        ax2.plot(common_evals[zoom_mask], summary_median[zoom_mask], color='indianred', linestyle='-.', linewidth=2, label='Median Run')
        ax2.plot(common_evals[zoom_mask], summary_min[zoom_mask], color='darkred', linestyle='-', linewidth=2, label='Best Run')

        # Smart Y-Axis Limiting
        y_lower = summary_min[zoom_mask].min() * 0.98
        y_upper = summary_max.iloc[-1] * 1.10
        ax2.set_ylim(y_lower, y_upper)

        ax2.set_title(f'Refinement Phase (After {cutoff_eval} Evals)', fontsize=13, fontweight='bold')
        ax2.set_xlabel('Evaluations', fontsize=12)
        ax2.set_ylabel('Fitness (Zoomed Scale)', fontsize=12)
        ax2.legend()
        ax2.grid(True, linestyle='--', alpha=0.5)

    # Adjust layout to prevent title overlap
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    save_dir = os.path.dirname(log_path)
    output_filename = os.path.join(save_dir, f'runs_trend_{instance_name}.png')

    plt.savefig(output_filename, dpi=300)
    plt.close()
    print(f"SUCCESS: Saved {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Path to the directory containing log CSVs (e.g., results/)')
    parser.add_argument('-c', '--cutoff', type=int, default=30000, help='Zoom cutoff')
    args = parser.parse_args()

    found_csv = False
    for root, dirs, files in os.walk(args.dir):
        for file in files:
            if file.endswith('.csv') and 'route_log_dynamic' in file:
                csv_path = os.path.join(root, file)
                plot_trend(csv_path, args.cutoff)
                found_csv = True

    if not found_csv:
        print(f"No valid CSV files found in directory: {args.dir}")