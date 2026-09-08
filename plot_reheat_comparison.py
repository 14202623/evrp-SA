import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os

# 1. Create directory to save figures
save_dir = "figures"
os.makedirs(save_dir, exist_ok=True)

# 2. Load experimental data with and without reheat
df_no_reheat = pd.read_csv('results/X-n143-k7_alpha_0.99985.csv')
df_with_reheat = pd.read_csv('results/no_reheating.X-n143-k7.evrp.csv')

def get_best_run_trajectory(df):
    """
    Extracts the evaluation and fitness trajectory of the best run.
    """
    if 'Run' in df.columns:
        final_costs = df.groupby('Run')['Best_Fitness'].last()
        best_run_id = final_costs.idxmin()
        best_run_df = df[df['Run'] == best_run_id]
        return best_run_df['Evaluations'].values, best_run_df['Best_Fitness'].values
    else:
        breakpoints = [0] + df[df['Evaluations'].diff() < 0].index.tolist() + [len(df)]
        best_chunk = None
        min_final_cost = float('inf')
        
        for i in range(len(breakpoints) - 1):
            chunk = df.iloc[breakpoints[i]:breakpoints[i+1]]
            final_cost = chunk['Best_Fitness'].iloc[-1]
            if final_cost < min_final_cost:
                min_final_cost = final_cost
                best_chunk = chunk
                
        return best_chunk['Evaluations'].values, best_chunk['Best_Fitness'].values

x_no, y_no = get_best_run_trajectory(df_no_reheat)
x_re, y_re = get_best_run_trajectory(df_with_reheat)

# 3. Plot the main convergence comparison figure
fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(x_no, y_no, color='#1f77b4', linestyle='--', linewidth=2, label='Without Reheat (Monotonic Cooling)')
ax.plot(x_re, y_re, color='crimson', linestyle='-', linewidth=2, label='With Reheat Mechanism (Proposed)')

ax.set_title('Impact of Temperature Reheating on Convergence (X-n143-k7)', fontsize=14, fontweight='bold')
ax.set_xlabel('Evaluations', fontsize=12)
ax.set_ylabel('Best Fitness (Cost)', fontsize=12)
ax.legend(fontsize=11, loc='upper right')
ax.grid(True, linestyle='--', alpha=0.5)

# 4. Configure zoomed inset axes focusing on escape from local optima
max_evals = max(x_no[-1], x_re[-1])
zoom_start = int(max_evals * 0.2)
zoom_end = int(max_evals * 0.8)

axins = ax.inset_axes([0.22, 0.25, 0.45, 0.45]) 
axins.plot(x_no, y_no, color='#1f77b4', linestyle='--', linewidth=1.5)
axins.plot(x_re, y_re, color='crimson', linestyle='-', linewidth=1.5)

axins.set_xlim(zoom_start, zoom_end)

mask_no = (x_no >= zoom_start) & (x_no <= zoom_end)
mask_re = (x_re >= zoom_start) & (x_re <= zoom_end)
ymin = min(y_no[mask_no].min(), y_re[mask_re].min()) - 200
ymax = max(y_no[mask_no].max(), y_re[mask_re].max()) + 200
axins.set_ylim(ymin, ymax)

axins.set_title('Escape from Local Optima Zoom', fontsize=10)
axins.grid(True, linestyle=':', alpha=0.5)
axins.ticklabel_format(style='sci', axis='x', scilimits=(0,0))

ax.indicate_inset_zoom(axins, edgecolor="black")

plt.tight_layout()
# Updated output filename
save_path = os.path.join(save_dir, 'reheat_mechanism_comparison.png')
plt.savefig(save_path, dpi=300, bbox_inches='tight')
print(f"Plot successfully saved to: {save_path}")

plt.show()