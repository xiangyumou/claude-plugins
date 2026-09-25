"""Post-training dynamics for VIGIL vs. DPO and DA-DPO (single panel).

Score on highly vision-dependent tasks against post-training steps. All three
methods start from the same SFT checkpoint (step 0), drawn as a gray dashed
"SFT only" reference line.

Techniques worth borrowing:
  - a line whose opacity increases left to right (a LineCollection with per-segment
    RGBA colours) to suggest progress over training, with solid markers on top so
    the data points stay fully visible;
  - hand-built legend handles (Line2D) because LineCollections have no simple
    legend entry;
  - y-axis from 0 so the relative gains are not exaggerated.

Run:  python plot_posttraining.py   ->  figures/comparison_posttraining.{png,pdf}
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D

FIG_DIR = Path(__file__).resolve().parent / 'figures'

data_posttraining = {
    'methods': [
        'DPO',
        'DA-DPO',
        'VIGIL (Ours)',
    ],
    'colors': [
        "#D88F8A",
        "#8BCF8B",
        "#0F4D92"
    ],
    'steps': [0, 200, 400, 600, 800],
    'results': np.array([  # shape (n_methods, n_steps)
        [22.0, 25.5, 28.2, 29.5, 30.2],
        [22.0, 33.5, 38.2, 39.8, 40.5],
        [22.0, 52.5, 56.8, 57.9, 58.5],
    ]),
}


def plot_curves(data_posttraining):
    methods = data_posttraining['methods']
    colors = data_posttraining['colors']

    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(1, 1, 1)
    x = np.asarray(data_posttraining['steps'])
    results = data_posttraining['results']
    x_pos = np.arange(len(x))  # steps are evenly spaced, so categorical positions are exact
    # Step 0 is the shared SFT checkpoint: use it as the reference level.
    ax.axhline(y=results[0][0], color='black', alpha=0.3, linewidth=4, linestyle='--')
    for color, y in zip(colors, results):
        # One segment per interval, alpha increasing left to right.
        pts = np.column_stack([x_pos, y])
        segments = np.stack([pts[:-1], pts[1:]], axis=1)
        alphas = np.linspace(0.3, 0.9, len(segments))
        rgb = to_rgba(color)[:3]
        lc = LineCollection(segments, colors=[(*rgb, a) for a in alphas], linewidths=3, capstyle='round')
        ax.add_collection(lc)
        ax.plot(x_pos, y, color=color, linewidth=0, marker='o', markersize=10)

    # Legend with line + marker for each method (LineCollections need proxy handles).
    handles = [Line2D([0], [0], color='black', linestyle='--', linewidth=4, alpha=0.3, label='SFT only')]
    for method, color in zip(methods, colors):
        handles.append(Line2D([0], [0], color=color, linewidth=3, marker='o', markersize=10, label=method))
    ax.legend(handles=handles, fontsize=20, loc='lower right', ncols=2, frameon=False)

    ax.set_xlabel('Post-training steps', fontsize=28, labelpad=12)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([str(b) for b in x])
    ax.set_ylabel('Performance on highly\nvision-dependent tasks' + r'$\uparrow$', fontsize=28, labelpad=12)
    ax.set_yticks([0, 20, 40, 60])
    ax.tick_params(labelsize=20, length=8, width=1.5)

    fig.tight_layout(pad=2)
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / 'comparison_posttraining.png', dpi=300)
    fig.savefig(FIG_DIR / 'comparison_posttraining.pdf')
    plt.close(fig)


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 24
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.linewidth'] = 3
    plt.rcParams['pdf.fonttype'] = 42  # embed TrueType, not Type 3
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    plot_curves(data_posttraining)
