"""Cumulative publication counts per month, annotated with LLM / VLM release dates.

Figure from a literature review of large language models in ophthalmology
(ChenLiu-1996/figures4papers, CC BY-NC 4.0). Two stacked panels share the same
monthly x axis: text-only studies (top) and multimodal studies (bottom). In each
panel the "Evaluation / Application" and "Methodological Contribution" areas are
both filled from zero and overlaid (not stacked), with a dark outline on top.

Techniques worth borrowing:
- ``mark_events``: arrows from a label down to the curve at a given month, with a
  per-label lift (``*`` suffixes) to stop neighbouring labels from colliding.
- Several events in the same month are passed as a list of (month, label) pairs,
  so none of them is silently overwritten (a dict with duplicate keys would be).
- Months are plotted at integer positions with 'YYYY-MM' tick labels on every
  January and July, so tick placement does not depend on the start month.
- Hatched fills with a black hatch but no black outline: draw the hatched fill,
  then re-draw its outline in white to hide it, then draw the curve on top.

Run: ``python plot_trend.py`` -> figures/trend_by_month.png and .pdf
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta


FIG_DIR = Path(__file__).resolve().parent / 'figures'

DATA = {
    'names': ['Methodological Contribution (Text-only)', 'Evaluation / Application (Text-only)',
              'Methodological Contribution (Multimodal)', 'Evaluation / Application (Multimodal)'],
    # One row per entry in 'names', one column per month starting at 'start'.
    'pub_by_month': np.array(
        [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 2, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2],
         [0, 0, 4, 0, 0, 6, 1, 3, 2, 0, 5, 0, 4, 0, 9, 1, 3, 4, 7, 6, 7, 6, 6, 1, 6, 4, 6, 2, 0, 0, 0, 1, 1],
         [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0],
         [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 1, 2, 1, 0, 2, 3, 0, 1, 2, 0, 2, 0, 1, 0, 0, 0, 0, 0, 0]]
    ),
    'start': (2022, 11),
    # (month, label) or (month, label, dx) tuples. Each trailing `*` lifts the label a
    # bit higher; dx (in months) nudges a label sideways away from a neighbouring arrow.
    # Months must be zero-padded 'YYYY-MM'; months outside the data window are skipped.
    'dates_llm': [
        ('2022-11', 'ChatGPT\n(GPT-3.5)'),
        ('2023-02', 'Bard\nLLaMA 1', -0.15), # both released in Feb 2023: one shared arrow
        ('2023-03', 'GPT-4**'),
        ('2023-07', 'LLaMA 2'),
        ('2023-12', 'Gemini 1.0'),
        ('2024-02', 'Gemini 1.5'),
        ('2024-04', 'LLaMA 3'),
        ('2024-12', 'Gemini 2.0'),
        ('2025-04', 'LLaMA 4'),
        ('2025-06', 'Gemini 2.5*'),
        ('2025-08', 'GPT-5'),               # after the data window (ends 2025-07): not drawn
    ],
    'dates_vlm': [
        ('2023-02', 'BLIP-2'),
        ('2023-04', 'LLaVA 1.0'),           # arXiv 2304.08485 (the published figure had 2023-07)
        ('2023-09', 'GPT-4V'),
        ('2023-10', 'LLaVA 1.5*'),
        ('2023-12', 'Gemini 1.0'),
        ('2024-02', 'Gemini 1.5'),
        ('2024-12', 'Gemini 2.0'),
        ('2025-06', 'Gemini 2.5'),
    ],
}


def month_year_list(start_year, start_month, n_months):
    start = datetime(start_year, start_month, 1)
    return [(start + relativedelta(months=i)).strftime('%Y-%m') for i in range(n_months)]


def mark_events(ax, time_arr, y_curve, events, dy=0.1):
    """Arrow + label above `y_curve` at each event month. Call after set_ylim."""
    x_idx = {t: i for i, t in enumerate(time_arr)}
    y0, y1 = ax.get_ylim()
    for date, label, *opt in events:
        if date not in x_idx:
            continue
        i = x_idx[date]
        dx = opt[0] if opt else 0.0
        lift = 1 + 0.8 * label.count('*')
        ax.annotate(
            label.replace('*', ''),
            xy=(i, y_curve[i]),
            xytext=(i + dx, y_curve[i] + lift * dy * (y1 - y0)),
            ha='center',
            va='bottom',
            fontsize=11,
            arrowprops=dict(arrowstyle='-|>', lw=1.3, color='black',
                            shrinkA=0, shrinkB=0, mutation_scale=15)
        )


def plot_curve(fig_path: Path):
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 15
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.linewidth'] = 2
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'
    colors = ["#9BC8FA", "#ffa8a6", "#13457E", "#850c0a"]  # light fills, dark outlines

    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(14, 8))

    cumsum = np.cumsum(DATA['pub_by_month'], axis=1)
    num_months = cumsum.shape[1]
    time_arr = month_year_list(*DATA['start'], n_months=num_months)
    x = np.arange(num_months)
    # A tick on every January and July, labelled 'YYYY-MM'.
    tick_idx = [i for i, t in enumerate(time_arr) if t.endswith(('-01', '-07'))]

    # Top: text-only. Areas overlap (both start at 0); evaluation is always the larger one.
    ax = fig.add_subplot(2, 1, 1)
    ax.fill_between(x, 0, cumsum[1], facecolor=colors[1], label=DATA['names'][1])
    ax.fill_between(x, 0, cumsum[0], facecolor=colors[0], label=DATA['names'][0])
    ax.plot(x, cumsum[0], lw=3, c=colors[2])
    ax.plot(x, cumsum[1], lw=3, c=colors[3])
    ax.legend(frameon=False, loc='upper left')
    ax.set_xticks(x[tick_idx], labels=[time_arr[i] for i in tick_idx])
    ax.set_ylim([0, 105])
    ax.set_ylabel('Cumulative\nPublication Count\n(Text-only)')
    mark_events(ax, time_arr, cumsum[1], DATA['dates_llm'])

    # Bottom: multimodal, same encoding plus hatches.
    ax = fig.add_subplot(2, 1, 2)
    for row, fill, hatch in ((3, colors[1], '\\\\\\'), (2, colors[0], '///')):
        # Hatch lines take the edge colour, so draw with a black edge...
        ax.fill_between(x, 0, cumsum[row], facecolor=fill, hatch=hatch,
                        edgecolor='black', label=DATA['names'][row])
        # ...then paint over the black polygon outline in white to "erase" it.
        ax.fill_between(x, 0, cumsum[row], facecolor='none', edgecolor='white', linewidth=2)
    ax.plot(x, cumsum[2], lw=3, c=colors[2])
    ax.plot(x, cumsum[3], lw=3, c=colors[3])
    ax.legend(frameon=False, loc='upper left')
    ax.set_xticks(x[tick_idx], labels=[time_arr[i] for i in tick_idx])
    ax.set_ylim([0, 24])
    ax.set_ylabel('Cumulative\nPublication Count\n(Multimodal)')
    mark_events(ax, time_arr, cumsum[3], DATA['dates_vlm'])

    fig.tight_layout(pad=2)
    fig.savefig(fig_path.with_suffix('.png'), dpi=300)
    fig.savefig(fig_path.with_suffix('.pdf'))
    plt.close(fig)


if __name__ == '__main__':
    plot_curve(FIG_DIR / 'trend_by_month')
