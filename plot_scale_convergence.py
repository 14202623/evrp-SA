import pandas as pd
import matplotlib.pyplot as plt
import os

# 1. Create directory for saving figures
save_dir = "figures"
os.makedirs(save_dir, exist_ok=True)

# 2. Load convergence logs for different problem scales
df_small = pd.read_csv('results/E-n33-k4/route_log_dynamic.E-n33-k4.evrp.csv')
df_medium = pd.read_csv('results/E-n76-k7/route_log_dynamic.E-n76-k7.evrp.csv')
df_large = pd.read_csv('results/X-n143-k7/route_log_dynamic.X-n143-k7.evrp.csv')

def plot_multiple_runs(ax, df, color, title):
    """
    Plots multi-run convergence trajectories by splitting data at evaluation resets.
    """
    if 'Run' in df.columns:
        for run_id, group in df.groupby('Run'):
            ax.plot(group['Evaluations'], group['Best_Fitness'], color=color, alpha=0.3, linewidth=1)
    else:
        breakpoints = [0] + df[df['Evaluations'].diff() < 0].index.tolist() + [len(df)]
        for i in range(len(breakpoints) - 1):
            chunk = df.iloc[breakpoints[i]:breakpoints[i+1]]
            ax.plot(chunk['Evaluations'], chunk['Best_Fitness'], color=color, alpha=0.3, linewidth=1)
            
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Evaluations', fontsize=12)
    ax.set_ylabel('Best Fitness (Cost)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.ticklabel_format(style='sci', axis='x', scilimits=(0,0))

# 3. Generate cross-scale subplot comparison
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

plot_multiple_runs(axes[0], df_small, '#2ca02c', 'Small: E-n33-k4')
plot_multiple_runs(axes[1], df_medium, '#1f77b4', 'Medium: E-n76-k7')
plot_multiple_runs(axes[2], df_large, '#d62728', 'Large: X-n143-k7')

plt.tight_layout()

# 4. Save and close the figure (Changed output filename here)
save_path = os.path.join(save_dir, 'scale_convergence_comparison.png')
plt.savefig(save_path, dpi=300, bbox_inches='tight')
print(f"Plot successfully saved to: {save_path}")

plt.show()