"""Cflows ablation: baselines vs. Cflows variants on four metrics (one panel per metric).

From the Cflows paper figures (ChenLiu-1996/figures4papers). Each panel is one metric
(RMSE, MAE lower is better; PCC, SCC higher is better), one bar per method, error bars
= std as reported in the source (the number of runs is not given there). A fifth,
axis-less subplot holds the shared legend.

Techniques worth borrowing:
  - one `ax.bar` call per panel with a list of colours AND a list of labels, so the
    legend handles come straight from `ax.get_legend_handles_labels()`;
  - colour roles: greens/red for competing methods, three tints of one blue for the
    ablation ladder (lighter = fewer components, darkest = full model);
  - metric direction shown in the y-label with mathtext arrows ($\\downarrow$/$\\uparrow$);
  - legend-only panel instead of a legend drawn over the data.

Run:  python plot_comparison_Ablation.py  ->  figures/figX_comparison_Ablation.{png,pdf}
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

FIG_DIR = Path(__file__).resolve().parent / 'figures'

data_comparison_Ablation = {
    'methods': [r'OT-CFM', r'SB-CFM', r'SF2M', r'Cflows (w/o growth + energy)', r'Cflows (w/o growth)', r'Cflows'],
    'colors': ['#AADCA9', '#8BCF8B', '#E9A6A1', '#B8C9E5', '#7097CA', '#3775BA'],
    'metrics': [r'RMSE$\downarrow$', r'MAE$\downarrow$', r'PCC$\uparrow$', r'SCC$\uparrow$'],
    'mean': {
        r'RMSE$\downarrow$': np.array([0.94, 1.05, 0.99, 0.89, 0.75, 0.62]),
        r'MAE$\downarrow$': np.array([0.75, 0.85, 0.78, 0.70, 0.59, 0.48]),
        r'PCC$\uparrow$': np.array([0.53, 0.49, 0.55, 0.58, 0.65, 0.72]),
        r'SCC$\uparrow$': np.array([0.50, 0.47, 0.52, 0.55, 0.68, 0.70]),
    },
    'std': {
        r'RMSE$\downarrow$': np.array([0.08, 0.09, 0.09, 0.07, 0.06, 0.05]),
        r'MAE$\downarrow$': np.array([0.07, 0.08, 0.07, 0.06, 0.05, 0.04]),
        r'PCC$\uparrow$': np.array([0.04, 0.02, 0.01, 0.03, 0.02, 0.02]),
        r'SCC$\uparrow$': np.array([0.03, 0.02, 0.03, 0.03, 0.03, 0.01]),
    },
}


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 24
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.linewidth'] = 3
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    fig = plt.figure(figsize=(35, 7))

    num_methods = len(data_comparison_Ablation['methods'])
    for metric_idx, metric_name in enumerate(data_comparison_Ablation['metrics']):
        ax = fig.add_subplot(1, 5, metric_idx + 1)

        ax.bar(
            np.arange(num_methods),
            data_comparison_Ablation['mean'][metric_name],
            yerr=data_comparison_Ablation['std'][metric_name],
            capsize=8,
            error_kw={'capthick': 2},
            color=data_comparison_Ablation['colors'],
            label=data_comparison_Ablation['methods'],
        )

        if metric_idx == 0:
            handles, labels = ax.get_legend_handles_labels()

        ax.set_xticks([])  # methods are named in the legend
        ax.set_ylabel(metric_name, fontsize=36, labelpad=12)
        # All metrics live in [0, ~1]: plain decimal ticks. (The original used
        # scientific notation, which put a "1e-1" offset on three panels but not on
        # RMSE, so the same value 0.6 read as "6" in one panel and "0.6" in another.)
        ax.yaxis.set_major_formatter('{x:.1f}')

    ax = fig.add_subplot(1, 5, 5)
    ax.legend(handles, labels, fontsize=30, loc='lower left', frameon=False)
    ax.set_axis_off()

    fig.tight_layout(pad=2)

    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / 'figX_comparison_Ablation.png', dpi=300)
    fig.savefig(FIG_DIR / 'figX_comparison_Ablation.pdf', dpi=300)
    plt.close(fig)
