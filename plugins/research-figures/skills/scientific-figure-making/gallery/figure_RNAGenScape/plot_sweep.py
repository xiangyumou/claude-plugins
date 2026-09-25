r"""RNAGenScape: sensitivity to the number of optimisation steps (two line panels).

Sweep over the number of optimisation steps (1, 5, 10, 20, 40) for the
RNAGenScape paper. The left panel shows the median change in property, the
right panel the success rate (%). Pink lines are runs that increase the
property, navy lines runs that decrease it.

Techniques worth borrowing
* Unevenly spaced x values used directly as ticks (``set_xticks(x_values)``).
* Arrow in the axis label ($\uparrow$) to say which direction is better.
  The left panel has none, because better means up for one series and down
  for the other.
* Success rate on a full 0-100 axis, so the plateau is not exaggerated.
* One legend only, placed in the empty lower-right corner of the last panel.
* The two series also differ in lightness (light pink vs. navy), so they stay
  distinct in grayscale.

Run:  python plot_sweep.py  ->  figures/results_sweep.{png,pdf}

Source: ChenLiu-1996/figures4papers (CC BY-NC 4.0).
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

FIG_DIR = Path(__file__).resolve().parent / 'figures'

# Same metrics (keys = y-axis labels) for both optimisation directions.
results_increase = {
  r'Median change in property': [0.292, 0.5047563, 0.57401, 0.55921, 0.5471513271],
  r'Success rate $\uparrow$': [67.6, 77.3, 79.9, 79.4, 79.6],
}
results_decrease = {
  r'Median change in property': [-0.90106, -1.27954, -1.3083, -1.2785, -1.29],
  r'Success rate $\uparrow$': [75.9, 84.7, 84.9, 84.7, 85.1],
}


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 15
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.linewidth'] = 2
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    x_label = 'Optimization step'
    x_values = [1, 5, 10, 20, 40]

    keys = list(results_increase.keys())
    fig = plt.figure(figsize=(4.5 * len(keys), 4))
    for fig_idx, y_key in enumerate(keys):
        ax = fig.add_subplot(1, len(keys), fig_idx + 1)
        ax.plot(x_values,
                results_increase[y_key],
                linestyle='-', linewidth=3,
                marker='o', markersize=8,
                label='increase property',
                alpha=0.8,
                color="#ea84dd")
        ax.plot(x_values,
                results_decrease[y_key],
                linestyle='-', linewidth=3,
                marker='o', markersize=8,
                label='decrease property',
                alpha=0.8,
                color="#0f4d92")
        if 'Success rate' in y_key:
            ax.set_ylim([0, 100])
        ax.set_xticks(x_values)
        ax.set_xlabel(x_label, fontsize=16)
        ax.set_ylabel(y_key, fontsize=16)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        if fig_idx == len(keys) - 1:
            ax.legend(loc='lower right', frameon=False)

    fig.tight_layout(pad=1)
    FIG_DIR.mkdir(exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(FIG_DIR / f'results_sweep.{ext}', dpi=300)
    plt.close(fig)
