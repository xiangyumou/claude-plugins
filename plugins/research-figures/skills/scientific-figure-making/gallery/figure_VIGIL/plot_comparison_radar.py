"""Radar comparison of VIGIL vs. DPO and DA-DPO across 4 VLM backbones x 3 benchmarks.

One spoke per (backbone, benchmark) pair, grouped by benchmark (POPE_Adv,
MathVista, MMBench); one closed polygon per method.

Radial scales (read this before borrowing the design):
  The three benchmarks live on very different ranges (~48-60 vs. ~82-90), so a
  single absolute radial range would squash the differences between methods.
  Each benchmark therefore has its own offset, but every spoke uses the SAME
  scale: 5 points per ring, 20 points from centre to rim. Rings are regular,
  concentric polygons and every ring is labelled on every spoke, so a gap of
  N points has the same radial length on all spokes and the centre value can
  be read off (outermost label - 20). The radial axis does not start at zero,
  so enclosed areas are not proportional to scores: compare vertices along a
  spoke, not polygon areas.

Techniques worth borrowing:
  - polar axes with the default grid switched off and hand-drawn spokes and rings,
    which allows per-spoke tick labels;
  - tick labels rotated tangentially but flipped on the lower half so none are
    upside down, with a white box so they stay readable over the rings;
  - closing each polygon by repeating the first vertex.

Run:  python plot_comparison_radar.py   ->  figures/comparison_radar.{png,pdf}
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

FIG_DIR = Path(__file__).resolve().parent / 'figures'

data_comparison = {
    'methods': [
        r'DPO',
        r'DA-DPO',
        r'VIGIL (Ours)',
    ],
    'colors': [
        "#D88F8A",
        "#8BCF8B",
        "#0F4D92"
    ],
    # 'Backbone\nBenchmark' -> scores for [DPO, DA-DPO, VIGIL] (all SFT + method), from
    # Xiao, Liu et al., "Staying VIGILant", arXiv:2606.26387, Tables 1 and 2.
    # The identical POPE_Adv rows for Qwen2.5-VL-7B and LLaVA-OneVision-7B are not a
    # copy-paste error: the paper reports 82.8 / 84.2 / 86.9 for both backbones.
    'results': {
        'Qwen2.5-VL-7B\nPOPE$_{Adv}$': np.array([82.8, 84.2, 86.9]),
        'LLaVA-OneVision-7B\nPOPE$_{Adv}$': np.array([82.8, 84.2, 86.9]),
        'InternVL2.5-26B\nPOPE$_{Adv}$': np.array([85.5, 86.8, 89.4]),
        'Qwen2.5-VL-72B\nPOPE$_{Adv}$': np.array([84.5, 87.4, 89.8]),
        'Qwen2.5-VL-7B\nMathVista': np.array([48.0, 48.8, 49.5]),
        'LLaVA-OneVision-7B\nMathVista': np.array([50.8, 51.5, 52.8]),
        'InternVL2.5-26B\nMathVista': np.array([57.9, 58.8, 60.1]),
        'Qwen2.5-VL-72B\nMathVista': np.array([54.1, 55.4, 56.6]),
        'Qwen2.5-VL-7B\nMMBench': np.array([71.2, 72.0, 72.5]),
        'LLaVA-OneVision-7B\nMMBench': np.array([72.5, 73.0, 73.8]),
        'InternVL2.5-26B\nMMBench': np.array([79.5, 80.1, 81.3]),
        'Qwen2.5-VL-72B\nMMBench': np.array([77.2, 77.8, 78.5]),
    },
}

# Outermost ring value per benchmark. All benchmarks share RING_STEP and N_RINGS,
# i.e. the same number of points per unit radius on every spoke.
BENCHMARK_MAX = {
    'POPE$_{Adv}$': 90,  # rings 75, 80, 85, 90 (centre 70)
    'MathVista': 65,     # rings 50, 55, 60, 65 (centre 45)
    'MMBench': 85,       # rings 70, 75, 80, 85 (centre 65)
}
RING_STEP = 5
N_RINGS = 4
R_CENTER, R_RIM = 45, 90  # display radii of the centre and the rim


def _task_suffix(subtask_name):
    """Benchmark = part after the first newline (e.g. 'Qwen2.5-VL-7B\\nMathVista' -> 'MathVista')."""
    return subtask_name.split('\n', 1)[-1]


def _to_display(value, bench):
    """Map a benchmark score to a display radius (linear, same scale for every benchmark)."""
    hi = BENCHMARK_MAX[bench]
    lo = hi - RING_STEP * N_RINGS
    return R_CENTER + (R_RIM - R_CENTER) * (np.asarray(value, dtype=float) - lo) / (hi - lo)


def plot_radar(data_comparison):
    """Single radar chart. Each spoke = one (backbone, benchmark); one polygon per method."""
    methods = data_comparison['methods']
    colors = data_comparison['colors']
    subtask_names = list(data_comparison['results'].keys())
    scores = np.array(list(data_comparison['results'].values()))  # (n_subtasks, n_methods)
    subtask_benchmarks = [_task_suffix(st) for st in subtask_names]
    n_subtasks = len(subtask_names)

    # Fail loudly instead of silently clipping a score outside its benchmark's range.
    for name, bench, row in zip(subtask_names, subtask_benchmarks, scores):
        lo = BENCHMARK_MAX[bench] - RING_STEP * N_RINGS
        assert lo <= row.min() and row.max() <= BENCHMARK_MAX[bench], (name, row)

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='polar')
    ax.set_theta_zero_location('N')

    # Spokes go clockwise from the top. Repeat the first angle to close each polygon.
    angles = np.linspace(2 * np.pi, 0, n_subtasks, endpoint=False)
    angles_closed = np.append(angles, angles[0])

    for m in range(len(methods)):
        radii = np.array([_to_display(v, b) for v, b in zip(scores[:, m], subtask_benchmarks)])
        radii_closed = np.append(radii, radii[0])
        ax.plot(angles_closed, radii_closed, color=colors[m], linewidth=2, marker='o', markersize=4,
                label=methods[m], zorder=5)
        ax.fill(angles_closed, radii_closed, color=colors[m], alpha=0.05, zorder=1)

    ax.set_ylim(R_CENTER, R_RIM)
    ax.grid(False)
    ax.spines['polar'].set_visible(False)
    ax.set_yticks([])
    ax.set_xticks([])
    # Rings (regular concentric polygons, rim drawn darker) and spokes.
    for k in range(1, N_RINGS + 1):
        r = R_CENTER + (R_RIM - R_CENTER) * k / N_RINGS
        ax.plot(angles_closed, np.full_like(angles_closed, r), color='k',
                linewidth=0.8 if k == N_RINGS else 0.5, zorder=3)
    for a in angles:
        ax.plot([a, a], [R_CENTER, R_RIM], color='gray', linewidth=0.5, zorder=3)

    # Per-spoke ring labels, rotated tangentially and flipped on the lower half.
    # They sit a fixed distance beside the spoke (angular offset ~ 1/radius) so the
    # data markers, which lie ON the spokes, are never covered; drawn above the lines.
    label_box = dict(boxstyle='round,pad=0.1', facecolor='white', edgecolor='none', alpha=0.8)
    side_offset = 2.2  # in display-radius units
    for angle, bench in zip(angles, subtask_benchmarks):
        rot = round(np.degrees(angle)) % 360
        if 90 < rot <= 270:
            rot += 180
        for k in range(1, N_RINGS + 1):
            tick_val = BENCHMARK_MAX[bench] - RING_STEP * (N_RINGS - k)
            r = _to_display(tick_val, bench)
            ax.text(angle + side_offset / (r - R_CENTER), r, f'{tick_val:d}', fontsize=11,
                    ha='center', va='center', rotation=rot, rotation_mode='anchor',
                    bbox=label_box, zorder=6, clip_on=False)
    # One name per spoke, pushed further out at the sides where labels are wide.
    for angle, label in zip(angles, subtask_names):
        label_r = R_RIM + 8 + 10 * np.abs(np.sin(angle))
        ax.text(angle, label_r, label, fontsize=14, ha='center', va='center',
                clip_on=False, fontfamily='monospace')
    ax.legend(loc='upper right', bbox_to_anchor=(1.40, 0.05), fontsize=15, frameon=False)

    fig.tight_layout(pad=2)
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / 'comparison_radar.png', dpi=300, bbox_inches='tight')
    fig.savefig(FIG_DIR / 'comparison_radar.pdf', bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 24
    plt.rcParams['pdf.fonttype'] = 42  # embed TrueType, not Type 3
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    plot_radar(data_comparison)
