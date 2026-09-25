"""Per-metric bar panels and ablation bars for ImmunoStruct.

ImmunoStruct predicts peptide-MHC immunogenicity from structure, sequence and
biochemistry. These are the results figures of the paper: IEDB benchmark and the
CEDAR cancer-neoantigen set ("Cancer" below). Four figures are written:

- bars_comparison_{IEDB,Cancer}: one panel per metric (AUROC, AUPRC, Mean PPVn),
  one bar per method. The x ticks are hidden and a 4th, axis-less subplot holds
  the only legend, so the method names are listed once.
- bars_ablation_IEDB: horizontal bars, one row per combination of components.
  The labels are decoded from binary masks ("11001" -> "Structure + Sequence +
  Transfer Learning") and the rows get darker shades of the ImmunoStruct blue
  further up the list.
- bars_ablation_Cancer: three variants from the transfer/contrastive-learning sweep
  in three shades of the same blue.

Techniques worth borrowing: a legend-only panel, labels decoded from binary masks,
ablation shades made with `tint` (blending with white) rather than alpha, so the
colours stay opaque with crisp edges in PDF/EPS.

Axes: all bar axes start at zero. The original figures cut the axes at 0.5, 0.75 or
0.68, which exaggerated gaps that are smaller than the error bars (e.g. Mean PPVn
in the Cancer ablation). Starting at zero, the differences the paper describes are
still easy to see.
Error bars: SD over 5 runs for all three metrics (see raw_data.py).

The canvases are drawn at poster scale (24-28 in wide, 24/32 pt text) and scaled down
in the paper, as in the figures4papers originals.

Run:  python plot_bars.py  ->  figures/bars_{comparison,ablation}_{IEDB,Cancer}.{png,pdf}
"""
from pathlib import Path

import numpy as np
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt

from raw_data import data_comparison_IEDB, data_ablation_IEDB, data_comparison_Cancer, data_ablation_Cancer

FIGURE_DIR = Path(__file__).resolve().parent / 'figures'
BLUE = '#3775BA'  # ImmunoStruct (ours); also the base colour of the ablation shades


def tint(color, amount):
    """Blend `color` with white: amount=1 gives the colour, 0 gives white.

    On a white background this looks the same as alpha=amount, but the colour stays opaque.
    """
    rgb = np.array(mcolors.to_rgb(color))
    return tuple(1 - amount * (1 - rgb))


def decode_ablation(data_dict):
    """'11001' + ['Structure', 'Sequence', ...] -> 'Structure + Sequence + Transfer Learning'."""
    binary_list = data_dict['ablations']
    component_str = data_dict['components']
    decoded_list = []
    for binary_code in binary_list:
        assert len(binary_code) == len(component_str)
        decoded_str = []
        for i, c in enumerate(binary_code):
            if c == '1':
                decoded_str.append(component_str[i])
        decoded_list.append(' + '.join(decoded_str))
    return decoded_list


def save(fig, stem):
    FIGURE_DIR.mkdir(exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(FIGURE_DIR / f'{stem}.{ext}', dpi=600)
    plt.close(fig)


def plot_comparison(data, stem):
    """One panel per metric and one bar per method, plus a legend-only 4th panel."""
    fig = plt.figure(figsize=(28, 6))
    x = np.arange(len(data['methods']))

    for i, metric in enumerate(data['metrics']):
        ax = fig.add_subplot(1, 4, i + 1)
        # A list of labels gives every bar its own legend entry.
        ax.bar(x,
               data['mean'][:, i],
               yerr=data['std'][:, i],
               capsize=5,
               color=data['colors'],
               label=data['methods'])
        ax.set_xticks([])
        ax.set_ylabel(metric, fontsize=32)
        if i == 0:
            handles, labels = ax.get_legend_handles_labels()

    ax = fig.add_subplot(1, 4, 4)
    ax.legend(handles, labels)
    ax.set_axis_off()

    fig.tight_layout(pad=2)
    save(fig, stem)


def plot_ablation_IEDB(data, stem):
    """Horizontal bars, one row per component combination; labels on the first panel only."""
    fig = plt.figure(figsize=(24, 8))
    y = np.arange(len(data['ablations']))
    # Shade by row: rows further down the list (plotted higher, ending with the full model) are darker.
    colors = [tint(BLUE, a) for a in np.linspace(0.2, 1.0, len(y))]

    for i, metric in enumerate(data['metrics']):
        ax = fig.add_subplot(1, 3, i + 1)
        ax.barh(y,
                data['mean'][:, i],
                xerr=data['std'][:, i],
                color=colors,
                ecolor='k',
                capsize=5)
        if i == 0:
            ax.set_yticks(y, decode_ablation(data))
        else:
            ax.set_yticks([])
        ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=5, steps=[1, 2, 5, 10]))  # 0.1/0.2 steps
        ax.set_xlabel(metric, fontsize=32)

    fig.tight_layout(pad=2)
    save(fig, stem)


def plot_ablation_Cancer(data, stem):
    """Three variants from the sweep over (transfer learning, contrastive-loss weight)."""
    fig = plt.figure(figsize=(28, 6))

    # Each entry of data['coeffs'] is [use transfer learning, contrastive-loss weight].
    variants = {
        'ImmunoStruct': [True, 0.01],
        'No Contrastive Learning': [True, 0],
        'No Contrastive Learning &\nNo Transfer Learning': [False, 0],
    }
    items_shown = [data['coeffs'].index(c) for c in variants.values()]  # -> [6, 4, 0]
    colors = [tint(BLUE, a) for a in [1.0, 0.7, 0.4]]
    x = np.arange(len(items_shown))

    for i, metric in enumerate(data['metrics']):
        ax = fig.add_subplot(1, 4, i + 1)
        ax.bar(x,
               data['mean'][items_shown, i],
               yerr=data['std'][items_shown, i],
               capsize=5,
               color=colors,
               label=list(variants))
        ax.set_xticks([])
        ax.set_ylabel(metric, fontsize=32)
        if i == 0:
            handles, labels = ax.get_legend_handles_labels()

    ax = fig.add_subplot(1, 4, 4)
    ax.legend(handles, labels)
    ax.set_axis_off()

    fig.tight_layout(pad=2)
    save(fig, stem)


if __name__ == '__main__':
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans'],
        'font.size': 24,
        'axes.spines.right': False,
        'axes.spines.top': False,
        'axes.linewidth': 3,
        'pdf.fonttype': 42,  # embed TrueType, not Type 3
        'ps.fonttype': 42,
        'svg.fonttype': 'none',
    })

    plot_comparison(data_comparison_IEDB, 'bars_comparison_IEDB')
    plot_ablation_IEDB(data_ablation_IEDB, 'bars_ablation_IEDB')
    plot_comparison(data_comparison_Cancer, 'bars_comparison_Cancer')
    plot_ablation_Cancer(data_ablation_Cancer, 'bars_ablation_Cancer')
