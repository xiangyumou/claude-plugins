"""Ablation bar chart for CellSpliceNet (splicing prediction in C. elegans neurons).

One bar per model variant (full model, then each input modality removed), with
the full model's score drawn as a dashed reference line and a red arrow plus
"-0.0x" label showing how much each ablation loses.

Techniques worth borrowing:
- value labels printed *inside* the bar top, with the text colour picked from
  the bar colour's luminance (`is_dark`) so it stays readable on dark and light fills;
- dashed baseline + downward arrows (`ax.annotate` with an empty string) to show
  the drop relative to the full model, instead of making the reader subtract;
- the y-limit is raised above 1.0 (ticks stop at 1.0) to leave room for the legend
  inside the axes without covering any bar.

The value axis starts at zero, as bar charts should.

Run:  python plot_ablation.py   ->  figures/ablation.png (300 dpi) + figures/ablation.pdf
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt


data_ablation = {
    'methods': [
        r'CellSpliceNet',
        r'No Expression',
        r'No Structure',
        r'No ROI',
        r'No Sequence',
    ],
    'colors': ['#0F4D92', '#B4E6B4', '#AFE6E6', '#FFE080', '#D3D3D3'],
    'result': np.array([0.88, 0.84, 0.82, 0.81, 0.74]),
}


def is_dark(color_in_hex, threshold=128):
    """True if a '#RRGGBB' colour is dark enough to need white text on top."""
    color = color_in_hex.lstrip('#')
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)

    luminance = 0.299*r + 0.587*g + 0.114*b
    return luminance < threshold


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

    fig = plt.figure(figsize=(13, 13))

    ax = fig.add_subplot(1, 1, 1)
    num_methods = len(data_ablation['methods'])
    # A list of labels gives every bar its own legend entry (no x tick labels needed).
    bars = ax.bar(
        np.arange(num_methods),
        data_ablation['result'],
        color=data_ablation['colors'],
        label=data_ablation['methods'],
    )

    # Value labels just inside the top of each bar, white on dark fills, black on light.
    for bar, value, color in zip(bars, data_ablation['result'], data_ablation['colors']):
        textcolor = 'white' if is_dark(color) else 'black'
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() - 0.08,
                f'{value:.2f}', ha='center', va='bottom', fontsize=32, color=textcolor)

    # Horizontal reference line at the full model's score.
    baseline = data_ablation['result'][0]
    ax.axhline(y=baseline, color=data_ablation['colors'][0], linestyle='--', linewidth=4, alpha=0.7)

    # For each ablation: arrow from the baseline down to the bar top, drop printed above it.
    for bar, current_value in zip(bars[1:], data_ablation['result'][1:]):
        reduction = baseline - current_value
        x_pos = bar.get_x() + bar.get_width()  # right edge of the bar

        ax.annotate('', xy=(x_pos, current_value), xytext=(x_pos, baseline),
                    arrowprops=dict(arrowstyle='->', color='red', lw=4))
        ax.text(x_pos - 0.3, baseline + 0.005, r'$-$' + f'{reduction:.2f}',
                ha='left', va='bottom', fontsize=24, color='red')

    ax.set_ylabel('Spearman correlation', fontsize=54, labelpad=12)
    # Headroom above the tallest bar (ticks stop at 1.0) holds the legend.
    ax.set_ylim([0.0, data_ablation['result'].max() + 0.5])
    ax.set_yticks([0.0, 0.25, 0.50, 0.75, 1.0])
    ax.tick_params(axis='y', labelsize=36, length=10, width=2)
    ax.set_xticks([])

    ax.legend(bbox_to_anchor=(0.50, 1.08), loc='upper left', fontsize=36, frameon=False)

    fig.tight_layout(pad=2)

    out_dir = Path(__file__).resolve().parent / 'figures'
    out_dir.mkdir(exist_ok=True)
    fig.savefig(out_dir / 'ablation.png', dpi=300)
    fig.savefig(out_dir / 'ablation.pdf')
    plt.close(fig)
