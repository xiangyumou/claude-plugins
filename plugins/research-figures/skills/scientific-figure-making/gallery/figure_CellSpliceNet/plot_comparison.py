"""Per-metric method comparison for CellSpliceNet (splicing prediction), worm and human data.

One figure per dataset (C. elegans "worm" and human), each a row of three panels
(Spearman, Pearson, R^2). Every panel has one bar per method: mean over 3 repeats (runs/folds),
error bar = SD over those repeats (population SD, ddof=0), mean printed above the
error bar.

Techniques worth borrowing:
- a list passed as `label=` to `ax.bar` gives each bar its own legend entry, so
  the x axis needs no tick labels (the legend names the methods);
- colour roles: dark blue for the proposed method, a red ramp that fades from the
  strongest to the weakest-listed competitor;
- extra y headroom (limit = max + 0.5, ticks stop at 1.0) keeps the in-axes
  legend clear of the bars;
- the human panels contain negative scores, so their y axis extends below zero
  and a thin zero line marks where the bars start.

All value axes start at (or below) zero, as bar charts should.

Run:  python plot_comparison.py
      -> figures/comparison_worm.{png,pdf} and figures/comparison_human.{png,pdf} (PNG at 300 dpi)
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import gridspec as gridspec


data_comparison = {
    'methods': [
        r'CellSpliceNet',
        r'Pangolin',
        r'SpliceTransformer',
        r'SpliceAI',
        r'SpliceFinder',
        r'ViT',
        r'AlphaGenome',
        r'ESM2',
    ],
    # Blue = proposed method; competitors fade from strong to pale red in table order.
    'colors': ['#0F4D92', '#D4685F', '#DA7B73', '#DF8E87', '#E5A19B', '#EBB4AF', '#F1C7C3', '#F6DAD8'],
    'metrics': [r'Spearman correlation', r'Pearson correlation', r'R$^2$ score'],
    # Rows = methods (same order as 'methods'), columns = 3 repeats (runs/folds).
    'result_worm': {
        r'Spearman correlation': np.array([
            [0.909, 0.872, 0.906],
            [0.813, 0.825, 0.832],
            [0.786, 0.799, 0.815],
            [0.751, 0.715, 0.753],
            [0.725, 0.715, 0.752],
            [0.689, 0.722, 0.705],
            [0.637, 0.637, 0.636],
            [0.642, 0.649, 0.596],
        ]),
        r'Pearson correlation': np.array([
            [0.929, 0.863, 0.918],
            [0.846, 0.867, 0.870],
            [0.827, 0.844, 0.862],
            [0.751, 0.708, 0.768],
            [0.728, 0.721, 0.761],
            [0.694, 0.723, 0.713],
            [0.646, 0.648, 0.645],
            [0.616, 0.635, 0.599],
        ]),
        r'R$^2$ score': np.array([
            [0.863, 0.745, 0.843],
            [0.634, 0.672, 0.689],
            [0.604, 0.609, 0.714],
            [0.542, 0.483, 0.532],
            [0.354, 0.359, 0.440],
            [0.375, 0.415, 0.347],
            [0.399, 0.401, 0.401],
            [0.353, 0.387, 0.348],
        ]),
    },
    'result_human': {
        r'Spearman correlation': np.array([
            [0.512, 0.475, 0.461],
            [0.030, -0.002, -0.007],
            [-0.002, -0.016, -0.015],
            [0.318, 0.299, 0.319],
            [0.083, -0.011, 0.060],
            [0.056, 0.034, 0.050],
            [0.306, 0.297, 0.296],
            [0.325, 0.308, 0.316],
        ]),
        r'Pearson correlation': np.array([
            [0.479, 0.484, 0.449],
            [0.036, -0.002, -0.002],
            [0.004, -0.017, 0.007],
            [0.344, 0.327, 0.348],
            [0.110, -0.013, 0.060],
            [0.096, 0.080, 0.043],
            [0.342, 0.331, 0.330],
            [0.355, 0.340, 0.343],
        ]),
        r'R$^2$ score': np.array([
            [0.229, 0.235, 0.201],
            [-0.013, -0.037, -0.052],
            [-0.005, -0.004, -0.004],
            [0.110, 0.100, 0.114],
            [0.003, -0.002, -0.003],
            [0.000, -0.003, -0.001],
            [0.099, 0.103, 0.095],
            [0.123, 0.108, 0.114],
        ]),
    }
}


def plot_comparison(results, y_bottom, out_stem):
    """Draw one 1x3 row (one panel per metric) for `results` and save it as PNG + PDF."""
    fig = plt.figure(figsize=(45, 12))
    gs = gridspec.GridSpec(1, 3)

    num_methods = len(data_comparison['methods'])
    for metric_idx, metric_name in enumerate(data_comparison['metrics']):
        ax = fig.add_subplot(gs[metric_idx])

        means = results[metric_name].mean(axis=1)
        stds = results[metric_name].std(axis=1)
        bars = ax.bar(
            np.arange(num_methods),
            means,
            yerr=stds,
            error_kw={
                'elinewidth': 2,   # thickness of vertical error bar line
                'capthick': 2,     # thickness of caps
                'capsize': 15      # length of caps
            },
            color=data_comparison['colors'],
            label=data_comparison['methods'],
        )

        # Mean value just above the top of the error bar.
        for bar, value, value_std in zip(bars, means, stds):
            label = f'{value:.2f}'
            if label == '-0.00':  # tiny negatives (e.g. -0.004) would otherwise print as "-0.00"
                label = '0.00'
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + value_std + 0.02,
                    label, ha='center', va='bottom', fontsize=32, color='black')

        if y_bottom < 0:
            ax.axhline(0, color='black', linewidth=1.5, zorder=0)  # zero line when bars go negative

        ax.set_ylabel(metric_name, fontsize=54, labelpad=12)
        ax.set_ylim([y_bottom, results[metric_name].max() + 0.5])
        ax.set_xticks([])
        ax.set_yticks([0.00, 0.25, 0.50, 0.75, 1.00])
        ax.tick_params(axis='y', labelsize=36, length=10, width=2)

        ax.legend(bbox_to_anchor=(0.02, 1.08), loc='upper left', fontsize=36, frameon=False, ncols=2, columnspacing=0.6)

    fig.tight_layout(pad=2)

    out_dir = Path(__file__).resolve().parent / 'figures'
    out_dir.mkdir(exist_ok=True)
    fig.savefig(out_dir / f'{out_stem}.png', dpi=300)
    fig.savefig(out_dir / f'{out_stem}.pdf')
    plt.close(fig)


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 24
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.linewidth'] = 3
    # Embed TrueType fonts (IEEE/ACM reject Type 3) and keep SVG text editable.
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    plot_comparison(data_comparison['result_worm'], y_bottom=0.0, out_stem='comparison_worm')
    # Human scores dip below zero (down to about -0.05 incl. error bars).
    plot_comparison(data_comparison['result_human'], y_bottom=-0.08, out_stem='comparison_human')
