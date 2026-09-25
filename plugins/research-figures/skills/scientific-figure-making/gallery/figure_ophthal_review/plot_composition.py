"""Heatmap of publication counts: application task (rows) x clinical evaluation stage (columns).

Figure from a literature review of large language models in ophthalmology
(ChenLiu-1996/figures4papers, CC BY-NC 4.0). Each cell is the number of papers
for one task at one stage; rows are grouped into three application areas.

Techniques worth borrowing:
- Row and column totals appended to the tick labels as "(n = ...)", so the
  heatmap doubles as a contingency table with margins.
- Integer annotations (``annot=True, fmt='d'``) on a sequential map ('Reds')
  that starts at white for zero, with white grid lines between cells.
- Row groups shown with thicker white separators and rotated group names placed
  just left of the tick labels (offset measured from the drawn labels).
- Colour limits and colourbar ticks derived from the data (rounded up to a
  multiple of 5) instead of hard-coded.

Run: ``python plot_composition.py`` -> figures/composition_heatmap.png and .pdf
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
import seaborn as sns


FIG_DIR = Path(__file__).resolve().parent / 'figures'

DATA = {
    'clinical_stage': [
        'Benchmark\nEvaluation', 'Expert\nEvaluation', 'Retrospective\nClinical Validation',
        'Prospective\nPilot Study', 'Full\nClinical Trial',
    ],
    # group -> task -> counts per clinical stage (same order as 'clinical_stage').
    'pub_by_category':
        {
            'Clinical Workflow': {
                'Screening or Diagnosis': [10, 7, 10, 3, 0],
                'Report Generation': [2, 3, 3, 0, 0],
                'Treatment Planning or\nRecommendation': [2, 3, 3, 2, 0],
            },
            'Patient Support': {
                'Patient Question Answering': [5, 13, 1, 1, 0],
                'After Visit or Discharge\nSummary Generation': [0, 2, 0, 0, 0],
                'Consultation or Interview': [0, 1, 1, 0, 0],
                'Patient Education\nMaterial Generation': [1, 6, 0, 0, 0],
                'Physician Recommendation': [0, 1, 0, 0, 0],
            },
            'Education and\nTraining': {
                'Exam Taking': [19, 5, 0, 0, 0],
                'Medical Education and\nLearning Support': [3, 5, 0, 0, 0],
            }
        }
}


def plot_heatmap(fig_path: Path):
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    # Mathtext in the same sans font, so the italic "$n$" matches the labels (no LaTeX
    # install needed). 'cal' is set only to avoid a findfont lookup of 'cursive'.
    plt.rcParams['mathtext.fontset'] = 'custom'
    plt.rcParams['mathtext.rm'] = 'sans'
    plt.rcParams['mathtext.it'] = 'sans:italic'
    plt.rcParams['mathtext.cal'] = 'sans'
    plt.rcParams['font.size'] = 16
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.linewidth'] = 2
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(1, 1, 1)

    # Flatten group -> task -> counts into a (tasks x stages) matrix.
    group_names, group_sizes, task_names, value_arr = [], [], [], []
    for group, tasks in DATA['pub_by_category'].items():
        group_names.append(group)
        group_sizes.append(len(tasks))
        for task, counts in tasks.items():
            task_names.append(task)
            value_arr.append(counts)
    value_arr = np.array(value_arr, dtype=int)

    # Append marginal totals to the tick labels (new lists: DATA is not modified).
    row_labels = [f'{name}\n($n$ = {total})'
                  for name, total in zip(task_names, value_arr.sum(axis=1))]
    col_labels = [f'{name}\n($n$ = {total})'
                  for name, total in zip(DATA['clinical_stage'], value_arr.sum(axis=0))]

    vmax = 5 * int(np.ceil(value_arr.max() / 5))
    sns.heatmap(value_arr, annot=True, vmin=0, vmax=vmax, fmt='d', cmap='Reds',
                linewidths=1, linecolor='white', ax=ax, cbar=True,
                cbar_kws={'ticks': np.arange(0, vmax + 1, 5), 'label': 'Number of Publications'})
    ax.set_yticks(np.arange(len(row_labels)) + 0.5, labels=row_labels, rotation=0)
    ax.set_xticks(np.arange(len(col_labels)) + 0.5, labels=col_labels, rotation=0)

    # Group separators: thick white lines between row groups.
    boundaries = np.cumsum(group_sizes)
    for y in boundaries[:-1]:
        ax.axhline(y, color='white', lw=8)

    # Group names, rotated, just left of the widest row label.
    fig.canvas.draw()
    label_width_pt = max(t.get_window_extent().width for t in ax.get_yticklabels()) * 72 / fig.dpi
    for name, start, size in zip(group_names, boundaries - group_sizes, group_sizes):
        ax.annotate(name, xy=(0, start + size / 2), xycoords=('axes fraction', 'data'),
                    xytext=(-label_width_pt - 30, 0), textcoords='offset points',
                    rotation=90, ha='center', va='center', fontweight='bold')

    fig.tight_layout(pad=2)
    fig.savefig(fig_path.with_suffix('.png'), dpi=300)
    fig.savefig(fig_path.with_suffix('.pdf'))
    plt.close(fig)


if __name__ == '__main__':
    plot_heatmap(FIG_DIR / 'composition_heatmap')
