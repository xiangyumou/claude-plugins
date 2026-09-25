"""How LLMs respond when told their math brainteaser solution is wrong (self-correction).

Figure from the Brainteaser project (Han et al., "Creativity or Brute Force? Using
Brainteasers as a Window into the Problem-Solving Abilities of Large Language Models").
Top row ("LLM solution"): outcome categories when the model is asked to correct a solution
it produced itself; bottom row ("Human solution"): outcome categories when it is asked to
correct a human-written solution. Arrows in the titles say whether lower or higher is
better. One bar per model; y = fraction of the 14 puzzles.

Techniques worth borrowing:
- Small-multiple bar panels with a direction-of-goodness arrow (mathtext down/up arrow)
  in each title, so good and bad outcomes can share one layout.
- A legend spanning two free grid cells (gs[1, 3:]) of the shorter second row, reusing the
  handles of the first panel.
- Bold row labels on the left, because both rows contain a "Degenerate repetition" panel.

Run:  python plot_selfcorrection_math.py
      -> figures/selfcorrection_math.png and figures/selfcorrection_math.pdf
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import gridspec

FIGURE_DIR = Path(__file__).resolve().parent / 'figures'


# Counts out of 14 puzzles per model. Note (source data, left unchanged): the categories
# do not always add up to 14 -- deepseek-chat sums to 15 in the LLM table, and
# Qwen 1.5B / o3 sum to 13 / 12 in the human table.
data_math_correcting_llm = {
    'methods': [r'DeepSeek R1 Distill Qwen 1.5B',
                r'DeepSeek R1 Distill Qwen 14B',
                r'DeepSeek R1 Distill Llama 70B',
                r'deepseek-chat (Deepseek-V3)',
                r'deepseek-reasoner (Deepseek-R1)',
                r'OpenAI o3'],
    'colors': ['#DDF3DE', '#AADCA9', '#8BCF8B', '#F6CFCB', '#E9A6A1', '#3775BA'],
    'subtypes': [r'Fault denial$\downarrow$',
                 r'Error misattribution$\downarrow$',
                 r'Degenerate repetition or stuck$\downarrow$',
                 r'Flawed correction$\downarrow$',
                 r'Valid correction$\uparrow$'],
    'result': {
        r'Fault denial$\downarrow$': np.array([1, 0, 0, 1, 0, 0]) / 14,
        r'Error misattribution$\downarrow$': np.array([4, 4, 3, 1, 0, 1]) / 14,
        r'Degenerate repetition or stuck$\downarrow$': np.array([9, 2, 4, 0, 0, 0]) / 14,
        r'Flawed correction$\downarrow$': np.array([0, 1, 0, 1, 3, 2]) / 14,
        r'Valid correction$\uparrow$': np.array([0, 7, 7, 12, 11, 11]) / 14,
    },
}

data_math_correcting_human = {
    'methods': [r'DeepSeek R1 Distill Qwen 1.5B',
                r'DeepSeek R1 Distill Qwen 14B',
                r'DeepSeek R1 Distill Llama 70B',
                r'deepseek-chat (Deepseek-V3)',
                r'deepseek-reasoner (Deepseek-R1)',
                r'OpenAI o3'],
    'colors': ['#DDF3DE', '#AADCA9', '#8BCF8B', '#F6CFCB', '#E9A6A1', '#3775BA'],
    'subtypes': [r'False confession$\downarrow$',
                 r'Degenerate repetition or stuck$\downarrow$',
                 r'Justified denial$\uparrow$'],
    'result': {
        r'False confession$\downarrow$': np.array([8, 10, 10, 13, 14, 12]) / 14,
        r'Degenerate repetition or stuck$\downarrow$': np.array([5, 3, 2, 0, 0, 0]) / 14,
        r'Justified denial$\uparrow$': np.array([0, 1, 2, 1, 0, 0]) / 14,
    },
}


def plot_panel(ax, data, category, row_label=None):
    """One outcome category: one bar per model (colour = model) on a 0-1 axis."""
    ax.bar(np.arange(len(data['methods'])), data['result'][category], color=data['colors'],
           label=data['methods'], edgecolor='black', linewidth=2)
    ax.set_title(category, fontsize=30, pad=36)
    ax.set_ylabel('Probability', fontsize=30, labelpad=12)
    ax.set_ylim([0, 1])
    ax.set_xticks([])
    if row_label is not None:
        ax.annotate(row_label, xy=(0, 0.5), xycoords='axes fraction', xytext=(-150, 0),
                    textcoords='offset points', rotation=90, ha='center', va='center',
                    fontsize=32, fontweight='bold')


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

    fig = plt.figure(figsize=(36, 12))
    gs = gridspec.GridSpec(2, 5)

    for col, category in enumerate(data_math_correcting_llm['subtypes']):
        ax = fig.add_subplot(gs[0, col])
        plot_panel(ax, data_math_correcting_llm, category,
                   row_label='LLM solution' if col == 0 else None)
        if col == 0:
            handles, labels = ax.get_legend_handles_labels()   # reused for the legend panel

    for col, category in enumerate(data_math_correcting_human['subtypes']):
        plot_panel(fig.add_subplot(gs[1, col]), data_math_correcting_human, category,
                   row_label='Human solution' if col == 0 else None)

    ax = fig.add_subplot(gs[1, 3:])
    ax.legend(handles, labels, fontsize=30, loc='center', frameon=False)
    ax.set_axis_off()

    fig.tight_layout(pad=2)

    FIGURE_DIR.mkdir(exist_ok=True)
    fig.savefig(FIGURE_DIR / 'selfcorrection_math.png', dpi=300)
    fig.savefig(FIGURE_DIR / 'selfcorrection_math.pdf')
    plt.close(fig)
