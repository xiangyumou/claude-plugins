"""Gene-regulatory-network inference: graph edit distance of 9 methods on 3 graph sizes.

From the Cflows paper figures (ChenLiu-1996/figures4papers). One panel per synthetic
network size (|V| nodes, |E| edges, given as the x-label in mathtext), one bar per
method, error bars = std as reported in the source (number of runs not given there).
Lower graph edit distance is better. A fourth, axis-less subplot holds a two-column
legend.

Techniques worth borrowing:
  - muted pastel fills for the eight baselines and one saturated blue for "ours",
    so the proposed method pops without a call-out;
  - mathtext set notation in axis labels (r'$|\\mathcal{V}|$');
  - legend-only panel with `ncols=2` for a long method list.

Run:  python plot_comparison_GeneRegulatory.py  ->  figures/fig2_comparison_GeneRegulatory.{png,pdf}
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

FIG_DIR = Path(__file__).resolve().parent / 'figures'

data_comparison_GeneRegulatory = {
    'methods': [r'OCE', r'PC', r'mTE', r'mMI', r'NRI', r'DCRNN', r'GTS', r'NIR', r'GC (ours)'],
    'colors': ['#D0A3A3', '#EFE7B1', '#F4C2C2', '#D7C4E2', '#E5C09F', '#A8C6C2', '#B7D3B0', '#F5B5A0', '#3775BA'],
    'metric': 'Graph Edit Distance',
    'datasets': [
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (100, 137)',
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (150, 329)',
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (200, 507)',
    ],
    'mean': {
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (100, 137)':
            np.array([138.6, 140.4, 126.4, 51.2, 72.1, 158.14, 215.4, 62.7, 51.2]),
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (150, 329)':
            np.array([293.4, 317.2, 261.0, 99.8, 106.6, 303.79, 347.2, 86.3, 109.0]),
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (200, 507)':
            np.array([449.8, 495.6, 397.4, 162.8, 219.8, 508.25, 481.8, 159.2, 158.8]),
    },
    'std': {
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (100, 137)':
            np.array([3.5, 3.9, 2.4, 3.3, 6.2, 8.6, 13.8, 3.2, 3.3]),
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (150, 329)':
            np.array([2.9, 3.7, 2.2, 4.0, 5.4, 12.4, 19.3, 2.8, 6.4]),
        r'($|\mathcal{V}|$, $|\mathcal{E}|$) = (200, 507)':
            np.array([1.1, 6.5, 8.8, 6.2, 13.4, 23.6, 7.0, 11.6, 12.6]),
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

    num_methods = len(data_comparison_GeneRegulatory['methods'])
    for dataset_idx, dataset_name in enumerate(data_comparison_GeneRegulatory['datasets']):
        ax = fig.add_subplot(1, 4, dataset_idx + 1)

        ax.bar(
            np.arange(num_methods),
            data_comparison_GeneRegulatory['mean'][dataset_name],
            yerr=data_comparison_GeneRegulatory['std'][dataset_name],
            capsize=8,
            error_kw={'capthick': 2},
            color=data_comparison_GeneRegulatory['colors'],
            label=data_comparison_GeneRegulatory['methods'],
        )

        if dataset_idx == 0:
            handles, labels = ax.get_legend_handles_labels()

        ax.set_xticks([])  # methods are named in the legend
        ax.set_ylabel(data_comparison_GeneRegulatory['metric'], fontsize=36, labelpad=12)
        ax.set_xlabel(dataset_name, fontsize=36, labelpad=12)
        # Edit distances are counts (50-500): plain integer ticks read better than
        # the original scientific notation with a "1e2" offset.
        ax.yaxis.set_major_formatter('{x:.0f}')

    ax = fig.add_subplot(1, 4, 4)
    ax.legend(handles, labels, fontsize=30, loc='lower left', ncols=2, frameon=False)
    ax.set_axis_off()

    fig.tight_layout(pad=2)

    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / 'fig2_comparison_GeneRegulatory.png', dpi=300)
    fig.savefig(FIG_DIR / 'fig2_comparison_GeneRegulatory.pdf', dpi=300)
    plt.close(fig)
