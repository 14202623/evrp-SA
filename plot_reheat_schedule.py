import argparse
import glob
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

plt.style.use('seaborn-v0_8-white')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dataset', type=str, required=True)
    args = parser.parse_args()

    # Extract instance name and locate target directory
    dataset_name = os.path.basename(args.dataset).replace('.evrp', '').replace('.csv', '')
    target_dir = os.path.join('results', dataset_name)
    
    # Dynamically match log CSV files
    csv_files = glob.glob(os.path.join(target_dir, f'route_log_dynamic.{dataset_name}*.csv'))
    if not csv_files:
        print(f"❌ Error: Log CSV file not found in {target_dir}")
        return

    # Load and clean data
    df = pd.read_csv(csv_files[0])
    df.columns = df.columns.str.strip()
    
    # Filter data for the run with the global minimum Best_Fitness
    best_run_id = df.loc[df['Best_Fitness'].idxmin(), 'RunID']
    df = df[df['RunID'] == best_run_id].sort_values(by='Evaluations')
    
    # Filter data points where REHEAT was triggered
    reheat_df = df[df['Operator'] == 'REHEAT']

    # Create 2-row subplots matching Figure 5 layout
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=False)

    # ==========================================
    # Top Plot: Global Convergence & Reheat Schedule
    # ==========================================
    ax1.plot(df['Evaluations'], df['Best_Fitness'], color='#d62728', linewidth=1.8, label='Best Fitness')
    
    if not reheat_df.empty:
        ax1.vlines(x=reheat_df['Evaluations'], ymin=df['Best_Fitness'].min(), ymax=df['Best_Fitness'].max(), 
                   colors='#ff7f0e', alpha=0.25, linestyles='--', label='Reheat Triggered')

    ax1.set_title(f'Global Convergence & Reheat Schedule ({dataset_name})', fontsize=12, fontweight='bold', pad=10)
    ax1.set_ylabel('Best Fitness', fontsize=10)
    ax1.legend(loc='upper right', frameon=True)
    ax1.grid(True, linestyle=':', alpha=0.5)

    # ==========================================
    # Bottom Plot: Zoom-in View (Reheat & Breakthrough Mechanism)
    # ==========================================
    # Define evaluation range for the zoom-in window (adjust based on your instance)
    start_eval, end_eval = 2450000, 2850000
    zoom_df = df[(df['Evaluations'] >= start_eval) & (df['Evaluations'] <= end_eval)]

    if not zoom_df.empty:
        # Left Y-axis: Current Fitness scatter & Best Fitness line
        if 'Current_Fitness' in zoom_df.columns:
            ax2.scatter(zoom_df['Evaluations'], zoom_df['Current_Fitness'], color='#1f77b4', alpha=0.4, s=5, label='Current Fitness')
        ax2.plot(zoom_df['Evaluations'], zoom_df['Best_Fitness'], color='#d62728', linewidth=2.2, label='Best Fitness')
        
        ax2.set_xlabel('Evaluations', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Fitness (Cost)', fontsize=10, fontweight='bold')
        ax2.grid(True, linestyle=':', alpha=0.5)

        # Right Y-axis: Temperature spikes overlay
        if 'Temperature' in zoom_df.columns:
            ax2_temp = ax2.twinx()
            ax2_temp.plot(zoom_df['Evaluations'], zoom_df['Temperature'], color='#ff7f0e', linestyle='-', linewidth=1.5, alpha=0.85, label='Temperature')
            ax2_temp.set_ylabel('Temperature', fontsize=10, color='#ff7f0e', fontweight='bold')
            ax2_temp.tick_params(axis='y', labelcolor='#ff7f0e')
            ax2_temp.grid(False)

            # Combine legends from both Y-axes
            lines_1, labels_1 = ax2.get_legend_handles_labels()
            lines_2, labels_2 = ax2_temp.get_legend_handles_labels()
            ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right', frameon=True, framealpha=0.9)
        else:
            ax2.legend(loc='upper right', frameon=True)

        ax2.set_title(f'Zoom-in: Mechanism of Reheat-induced Exploration & Breakthrough ({start_eval/1e6:.2f}M - {end_eval/1e6:.2f}M)', fontsize=11, fontweight='bold', pad=8)

    plt.tight_layout()
    output_png = os.path.join(target_dir, f"fig5_reheat_schedule_{dataset_name}.png")
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Success! Saved Figure 5 plot to {output_png}")

if __name__ == "__main__":
    main()