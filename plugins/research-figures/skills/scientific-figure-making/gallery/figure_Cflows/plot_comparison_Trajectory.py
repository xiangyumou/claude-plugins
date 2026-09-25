"""Trajectory inference: 4 methods x 3 synthetic datasets on 3 error metrics (grouped bars).

From the Cflows paper figures (ChenLiu-1996/figures4papers); the proposed method is
labelled "BEMIOflow (ours)" in the source data. One panel per metric (all lower is
better), within each panel one cluster of bars per dataset. Means only: the source
reports no spread, so there are no error bars. A fourth, axis-less subplot holds the
legend.

Techniques worth borrowing:
  - grouped bars without `width` arithmetic: each dataset's cluster is placed at
    `arange(n_methods) + dataset_idx * (n_methods + 1)`, the "+1" leaving a one-bar
    gap between clusters, and the tick sits at the cluster centre;
  - a light-to-dark green ramp for the baselines and blue for the proposed method;
  - `ticklabel_format(style='sci', scilimits=(0, 0))` puts the common power of ten
    ("1e-3") on top of the axis instead of in every tick label.

Run:  python plot_comparison_Trajectory.py  ->  figures/fig2_comparison_Trajectory.{png,pdf}
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

FIG_DIR = Path(__file__).resolve().parent / 'figures'

data_comparison_Trajectory = {
    'methods': [r'TrajectoryNet', r'OT-CFM', r'SB-CFM', r'BEMIOflow (ours)'],
    'colors': ['#DDF3DE', '#AADCA9', '#8BCF8B', '#3775BA'],
    'metrics': ['PHATE Space RMSE', 'Gene Space RMSE', 'Interpolation EMD'],
    'datasets': ['Bifurcation', 'Cycle', 'Unidirectional'],
    'mean': {
        'PHATE Space RMSE': {
            'Bifurcation': np.array([6.16, 2.98, 2.83, 2.60]) * 1e-3,
            'Cycle': np.array([2.49, 3.79, 1.58, 0.777]) * 1e-3,
            'Unidirectional': np.array([8.08, 5.33, 5.67, 3.40]) * 1e-3,
        },
        'Gene Space RMSE': {
            'Bifurcation': np.array([0.150, 0.0842, 0.0835, 0.0773]),
            'Cycle': np.array([0.151, 0.209, 0.141, 0.118]),
            'Unidirectional': np.array([0.118, 0.0960, 0.0978, 0.0853]),
        },
        'Interpolation EMD': {
            'Bifurcation': np.array([1.07, 0.495, 0.516, 0.465]) * 1e-2,
            'Cycle': np.array([0.710, 0.818, 0.526, 0.465]) * 1e-2,
            'Unidirectional': np.array([1.50, 1.32, 1.28, 0.935]) * 1e-2,
        },
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

    fig = plt.figure(figsize=(36, 6))

    num_methods = len(data_comparison_Trajectory['methods'])
    for metric_idx, metric_name in enumerate(data_comparison_Trajectory['metrics']):
        ax = fig.add_subplot(1, 4, metric_idx + 1)
        xtick_list = []

        for dataset_idx, dataset_name in enumerate(data_comparison_Trajectory['datasets']):
            offset = dataset_idx * (num_methods + 1)  # one empty slot between clusters
            ax.bar(
                np.arange(num_methods) + offset,
                data_comparison_Trajectory['mean'][metric_name][dataset_name],
                color=data_comparison_Trajectory['colors'],
                label=data_comparison_Trajectory['methods'],
            )
            xtick_list.append(np.mean(np.arange(num_methods)) + offset)

        if metric_idx == 0:
            # Every cluster adds the same labels; keep the first cluster's handles.
            handles, labels = ax.get_legend_handles_labels()
            handles, labels = handles[:num_methods], labels[:num_methods]

        ax.set_xticks(xtick_list)
        ax.set_xticklabels(data_comparison_Trajectory['datasets'])
        ax.set_ylabel(metric_name, fontsize=36, labelpad=12)
        ax.set_xlabel('Dataset', fontsize=36, labelpad=12)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))  # >= 4 ticks on every panel
        ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))

    ax = fig.add_subplot(1, 4, 4)
    ax.legend(handles, labels, fontsize=30, loc='lower left', frameon=False)
    ax.set_axis_off()

    fig.tight_layout(pad=2)

    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / 'fig2_comparison_Trajectory.png', dpi=300)
    fig.savefig(FIG_DIR / 'fig2_comparison_Trajectory.pdf', dpi=300)
    plt.close(fig)
