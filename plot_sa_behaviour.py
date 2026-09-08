import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

def plot_sa_behavior(log_path):
    if not os.path.exists(log_path):
        return
        
    df = pd.read_csv(log_path)
    df.columns = df.columns.str.strip()
    
    # Filter for the first run if multiple runs exist
    if 'RunID' in df.columns:
        df = df[df['RunID'] == df['RunID'].min()].copy()

    df = df.sort_values(by='Evaluations')

    # Focus on the early convergence phase by removing post-reheat spikes
    diff = df['Current_Fitness'].diff()
    spike_condition = (diff > 50) & (df['Evaluations'] > 50000)
    
    if spike_condition.any():
        first_spike_eval = df.loc[spike_condition, 'Evaluations'].min()
        df = df[df['Evaluations'] < first_spike_eval]

    best_val = df['Best_Fitness'].min()
    convergence_point = df[df['Best_Fitness'] <= best_val * 1.05]['Evaluations'].min()
    max_eval = min(df['Evaluations'].max(), convergence_point * 2.5)
    df = df[df['Evaluations'] <= max_eval]

    fig, ax = plt.subplots(figsize=(10, 7))

    # 1. Background: Current Fitness scatter
    ax.scatter(df['Evaluations'], df['Current_Fitness'], 
               color='#7fc97f', s=14, alpha=0.35, label='Current Fitness', zorder=2)

    # 2. Main line: Best So Far trajectory
    ax.plot(df['Evaluations'], df['Best_Fitness'], 
            color='#d62728', linewidth=2.5, label='Best So Far', zorder=3)

    # 3. Core logic: Capture exact moments and operators that improved Best Fitness
    if 'Operator' in df.columns:
        df['Operator'] = df['Operator'].astype(str).str.strip()
        
        # Filter strictly decreasing Best_Fitness points (successful global improvements)
        best_diff = df['Best_Fitness'].diff()
        improved_mask = (best_diff < -1e-5) | (df.index == df.index[0])
        improved_df = df[improved_mask].copy()

        unique_ops = df['Operator'].unique()
        
        markers = ['p', 's', 'v', '^', 'D', 'o', 'P', 'X'] 
        colors = ['#17becf', '#ff7f0e', '#9467bd', '#e377c2', '#1f77b4', '#bcbd22', '#8c564b']
        
        op_marker_map = {op: markers[i % len(markers)] for i, op in enumerate(unique_ops)}
        op_color_map = {op: colors[i % len(colors)] for i, op in enumerate(unique_ops)}

        # Overlay operator markers onto the Best So Far curve when an improvement occurs
        for op in unique_ops:
            op_imp_df = improved_df[improved_df['Operator'] == op]
            if not op_imp_df.empty:
                ax.scatter(op_imp_df['Evaluations'], op_imp_df['Best_Fitness'],
                           color=op_color_map[op], marker=op_marker_map[op],
                           s=60, zorder=2, label=f'Best Improved by {op}',
                           edgecolors='none')

    ax.set_title('Operator Contributions to Best Solution Improvement', fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel('Evaluations', fontsize=12, fontweight='bold')
    ax.set_ylabel('Fitness (Cost)', fontsize=12, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)
    
    ax.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.95, fontsize=10)

    plt.tight_layout()
    output_filename = log_path.replace('.csv', '_operator_best_improvements.png')
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, type=str)
    args = parser.parse_args()
    
    for root, dirs, files in os.walk(args.dir):
        for file in files:
            if file.endswith('.csv'):
                plot_sa_behavior(os.path.join(root, file))