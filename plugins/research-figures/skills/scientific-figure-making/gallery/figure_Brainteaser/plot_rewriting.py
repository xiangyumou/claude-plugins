r"""Effect of rewriting math brainteasers on three reasoning models.

Figure from the Brainteaser project (Han et al., "Creativity or Brute Force? Using
Brainteasers as a Window into the Problem-Solving Abilities of Large Language Models").
Left: fraction of the 30 puzzles solved before vs after rewriting. Right: how each
model's result changed (correct -> incorrect, incorrect -> correct, unchanged).
Colour = model, hatch = condition; the two legends sit in their own axis-off panels.

Techniques worth borrowing:
- Grouped bars that encode two factors at once: colour for the model (per-bar colour
  list) and hatch for the condition, so no x tick labels are needed.
- Two legend-only panels (colour key and hatch key) built from throw-away bars.
- Mathtext arrows (r'$\rightarrow$') inside legend labels.

Run:  python plot_rewriting.py   ->  figures/rewriting.png and figures/rewriting.pdf
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import gridspec

FIGURE_DIR = Path(__file__).resolve().parent / 'figures'


data_rewriting_math = {
    'methods': [r'DeepSeek R1 Distill Llama 70B',
                r'deepseek-reasoner (Deepseek-R1)',
                r'OpenAI o3'],
    'colors': ['#8BCF8B', '#E9A6A1', '#3775BA'],
    # hatches: 'fig1' conditions use the first two, 'fig2' conditions the last three
    'hatch_styles': ['', '|', '\\', '/', '-'],
    'fig1': ['Before rewriting', 'After rewriting'],
    'fig2': [r'correct $\rightarrow$ incorrect', r'incorrect $\rightarrow$ correct', 'same result'],
    'result': {   # counts out of 30 puzzles
        'Before rewriting': np.array([7, 15, 17]) / 30,
        'After rewriting': np.array([10, 19, 22]) / 30,
        r'correct $\rightarrow$ incorrect': np.array([0, 2, 1]) / 30,
        r'incorrect $\rightarrow$ correct': np.array([3, 6, 6]) / 30,
        'same result': np.array([27, 22, 23]) / 30,
    },
}


def grouped_bars(ax, data, conditions, hatches, width, title):
    """One cluster per model; within it one bar per condition (colour = model, hatch = condition)."""
    num_methods = len(data['methods'])
    for idx, (condition, hatch) in enumerate(zip(conditions, hatches)):
        ax.bar(np.arange(num_methods) + width * idx * 1.1,   # 10% gap between bars in a cluster
               data['result'][condition], width=width, color=data['colors'],
               edgecolor='black', linewidth=2, hatch=hatch)
    ax.set_title(title, fontsize=36, pad=0)
    ax.set_ylabel('Probability', fontsize=30, labelpad=12)
    ax.set_ylim([0, 1.01])
    ax.set_xticks([])


def legend_panel(ax, labels, colors, hatches):
    """Legend-only panel: draw dummy bars, harvest their handles, then remove them."""
    bars = ax.bar(np.arange(len(labels)), np.ones(len(labels)), color=colors, label=labels,
                  hatch=hatches, edgecolor='black', linewidth=2)
    handles, legend_labels = ax.get_legend_handles_labels()
    for b in bars:
        b.remove()
    ax.legend(handles, legend_labels, fontsize=30, loc='center', frameon=False)
    ax.set_axis_off()


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 24
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.linewidth'] = 3
    plt.rcParams['pdf.fonttype'] = 42   # embed TrueType, not Type 3
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    data = data_rewriting_math
    fig = plt.figure(figsize=(24, 12))
    gs = gridspec.GridSpec(2, 2)

    grouped_bars(fig.add_subplot(gs[0, 0]), data, data['fig1'], data['hatch_styles'][:2],
                 width=0.3, title='Correctness')
    grouped_bars(fig.add_subplot(gs[0, 1]), data, data['fig2'], data['hatch_styles'][2:],
                 width=0.25, title='Change in Result')

    # Bottom row: colour key (models) and hatch key (conditions of both panels).
    legend_panel(fig.add_subplot(gs[1, 0]), data['methods'], data['colors'], '')
    legend_panel(fig.add_subplot(gs[1, 1]), data['fig1'] + data['fig2'], 'white',
                 data['hatch_styles'])

    fig.tight_layout(pad=2)

    FIGURE_DIR.mkdir(exist_ok=True)
    fig.savefig(FIGURE_DIR / 'rewriting.png', dpi=300)
    fig.savefig(FIGURE_DIR / 'rewriting.pdf')
    plt.close(fig)
