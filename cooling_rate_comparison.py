import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 1. Create a directory to save the figures
save_dir = "figures"
os.makedirs(save_dir, exist_ok=True)

# 2. Load data for the four cooling schedules
df_rapid_999 = pd.read_csv('results/E-n76-k7_alpha_0999.csv')
df_tuned = pd.read_csv('results/E-n76-k7_alpha_099985.csv')
df_slow = pd.read_csv('results/E-n76-k7_alpha_099990.csv')

def get_best_run_trajectory(df):
    """Extracts the evaluation and fitness trajectory of the best run."""
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

# Extract trajectories for all four setups
x_999, y_999 = get_best_run_trajectory(df_rapid_999)
x_tuned, y_tuned = get_best_run_trajectory(df_tuned)
x_slow, y_slow = get_best_run_trajectory(df_slow)

# 3. Plot the main figure
fig, ax = plt.subplots(figsize=(10, 6))

# Plot all four trajectories with distinct colors and linestyles
ax.plot(x_999, y_999, color='darkorange', linestyle='-.', linewidth=2, label=r'Rapid Cooling ($\alpha=0.999$)')
ax.plot(x_tuned, y_tuned, color='#1f77b4', linestyle='--', linewidth=2, label=r'Tuned Cooling ($\alpha=0.99985$)')
ax.plot(x_slow, y_slow, color='crimson', linestyle='-', linewidth=2, label=r'Slow Cooling ($\alpha=0.99990$)')

ax.set_title('Impact of Cooling Rate on Convergence Trajectory (E-n76-k7)', fontsize=14, fontweight='bold')
ax.set_xlabel('Evaluations', fontsize=12)
ax.set_ylabel('Best Fitness (Cost)', fontsize=12)
ax.legend(fontsize=12, loc='upper right')
ax.grid(True, linestyle='--', alpha=0.5)

# 4. Configure the inset (zoom) axes in the lower-middle-left region to avoid overlapping
# [left, bottom, width, height]
axins = ax.inset_axes([0.18, 0.22, 0.45, 0.45]) 
axins.plot(x_999, y_999, color='darkorange', linestyle='-.', linewidth=1.5)
axins.plot(x_tuned, y_tuned, color='#1f77b4', linestyle='--', linewidth=1.5)
axins.plot(x_slow, y_slow, color='crimson', linestyle='-', linewidth=1.5)

# Set the focus area for the zoom window (last 500,000 evaluations)
max_evals = max([x_999[-1], x_tuned[-1], x_slow[-1]])
window_start = max_evals - 500000
axins.set_xlim(window_start, max_evals)

# Dynamically calculate the y-axis limits for the zoomed region based on visible data
def get_min_max_in_window(x, y, x_min):
    mask = x >= x_min
    if not any(mask): return float('inf'), float('-inf')
    return y[mask].min(), y[mask].max()

y_mins, y_maxs = [], []
for x, y in [(x_999, y_999), (x_tuned, y_tuned), (x_slow, y_slow)]:
    c_min, c_max = get_min_max_in_window(x, y, window_start)
    if c_min != float('inf'): y_mins.append(c_min)
    if c_max != float('-inf'): y_maxs.append(c_max)

axins.set_ylim(min(y_mins) - 5, max(y_maxs) + 5)

axins.set_title('Late-stage Refinement Zoom', fontsize=10)
axins.grid(True, linestyle=':', alpha=0.5)
axins.ticklabel_format(style='sci', axis='x', scilimits=(0,0))

# Indicate the zoomed region on the main plot
ax.indicate_inset_zoom(axins, edgecolor="black")

plt.tight_layout()
save_path = os.path.join(save_dir, 'cooling_rate_comparison.png')
plt.savefig(save_path, dpi=300, bbox_inches='tight')
print(f"Plot successfully saved to: {save_path}")

plt.show()