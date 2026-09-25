r"""RNAGenScape: main comparison figures (speed bars + results table-heatmaps).

Two figures from the RNAGenScape paper (RNA property optimisation on a learned
manifold), comparing 12 baselines against RNAGenScape on three datasets
(OpenVaccine, Zebrafish, Ribosome), each optimised in both directions (+/-):

* ``results_comparison_speed``: inference throughput (samples / ms) of the
  guided generators vs. ours, one coloured bar per method, legend instead of
  x tick labels, exact values printed on the bars.
* ``results_comparison_optimization``: two annotated "table heatmaps"
  (median change in property, success rate) with methods as rows, a final
  italic *Improvement* row giving ours vs. the best baseline in % (relative,
  not percentage points), green if ours wins and dark red if not.

Techniques worth borrowing
* Per-column colour normalisation with ``imshow(..., extent=...)`` one column
  at a time: each column is shaded by its own range, so the colour ranks methods
  within a column and is not comparable across columns. That is why there is no
  colourbar; the value is printed in every cell.
* Direction-aware shading: "(+)" columns use Reds from 0 up, "(-)" columns use
  Blues_r from 0 down, so darker always means "moved further in the requested
  direction" and moves in the wrong direction stay white. Success-rate
  shading starts at 50 % (chance level), so anything below it is white.
* Summary row rendered as NaN (``cmap.with_extremes(bad="white")``) so it gets
  coloured text on a white background instead of a cell colour.
* Text colour switched between black and white from the cell's luminance.
* The speed chart uses a linear axis from zero. The original used log-scaled
  bars, where bar length depends on an arbitrary baseline. The small values
  (0.024, 0.006) become slivers but are still labelled with ``bar_label``.

Method and dataset names are set in monospace with mathtext (``$\mathtt{...}$``),
so no LaTeX installation is needed.

Run:  python plot_comparison.py
      -> figures/results_comparison_speed.{png,pdf}
      -> figures/results_comparison_optimization.{png,pdf}

Source: ChenLiu-1996/figures4papers (CC BY-NC 4.0).
"""
from pathlib import Path

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

FIG_DIR = Path(__file__).resolve().parent / 'figures'

summary_label = r'$\mathit{Improvement}$'
options = ['VAE', 'DDPM', 'LDM', 'FM',
           'DiffAb', 'IgLM', 'NOS-C', 'NOS-D',
           'OAE + gradient ascent',
           'OAE + MCMC',
           'OAE + hill climbing',
           'OAE + stochastic hill climbing',
           r'$\mathtt{RNAGenScape}$ $\mathbf{(ours)}$',
           summary_label]
# One colour per method (not for the summary row): grays = de novo generators,
# teal/pink/magenta = guided generators, greens = OAE + optimiser, navy = ours.
colors = ["#cdcdcd", "#767676", "#4d4d4d", "#272727",
          "#c4ece7", "#ecc4c4", "#ecc4e7", "#ea84dd",
          "#d5e29b", "#bdd35c", "#9fbc1d", "#8ead03",
          "#0f4d92"]
OURS = 12  # row index of RNAGenScape in `options` / `colors` / results lists

# Inference time per sample (ms); plotted as throughput = 1 / time.
results_inference = [0.13, 0.91, 0.74, 5.82, 41.04, 157.57, 0.99, 0.96,
                     0.50, 10.93, 81.52, 99.66, 0.57]
# Median change in property (delta) and success rate (%), per dataset and direction.
results_openvaccine_delta_pos = [-0.23, -0.33, -0.07, -0.34, 0.06, 0.24, 0.09, 0.18,
                                 -0.01, -0.11, 0.40, -0.12, 0.54]
results_openvaccine_pct_pos = [42.1, 33.8, 47.5, 32.5, 55.0, 63.1, 54.6, 58.3,
                               51.0, 45.1, 69.2, 43.5, 77.5]
results_openvaccine_delta_neg = [-0.23, -0.33, -0.07, -0.34, 0.11, 0.01, -2.25, -0.29,
                                 -0.19, -0.19, -0.29, -0.15, -2.81]
results_openvaccine_pct_neg = [57.9, 66.2, 52.5, 67.5, 44.0, 49.6, 90.6, 65.4,
                               61.3, 57.7, 64.2, 60.0, 97.9]
results_zebrafish_delta_pos = [-0.01, 0.29, -0.95, 0.32, -0.21, -0.57, 0.03, 0.31,
                               -1.21, -0.20, 0.76, 0.32, 0.77]
results_zebrafish_pct_pos = [49.4, 58.2, 22.5, 59.8, 36.3, 32., 51.1, 57.9,
                             18.0, 44.3, 74.4, 60.3, 75.0]
results_zebrafish_delta_neg = [-0.01, 0.29, -0.95, 0.32, -0.21, -0.83, -1.07, 0.38,
                               -0.33, -0.37, -0.87, -0.80, -1.29]
results_zebrafish_pct_neg = [50.6, 41.8, 77.5, 40.2, 60.8, 74.3, 80.8, 40.2,
                             66.5, 60.1, 75.2, 73.7, 85.1]
results_ribosome_delta_pos = [-0.24, -0.11, -0.24, -0.10, -0.05, 0.63, 0.08, -0.09,
                              0.43, -0.19, 0.53, 0.19, 0.63]
results_ribosome_pct_pos = [41.7, 45.9, 41.8, 46.4, 45.0, 80.5, 53.6, 46.5,
                            73.6, 43.0, 83.0, 60.4, 81.4]
results_ribosome_delta_neg = [-0.24, -0.11, -0.24, -0.10, -0.04, -0.51, 0.10, -0.10,
                              -0.05, -0.10, -0.06, -0.05, -0.58]
results_ribosome_pct_neg = [58.3, 54.1, 58.2, 53.6, 54.2, 65.5, 46.0, 53.6,
                            55.7, 54.2, 56.1, 55.2, 67.8]

column_labels = [r'$\mathtt{OpenVaccine}$ (+)', r'$\mathtt{OpenVaccine}$ (-)',
                 r'$\mathtt{Zebrafish}$ (+)', r'$\mathtt{Zebrafish}$ (-)',
                 r'$\mathtt{Ribosome}$ (+)', r'$\mathtt{Ribosome}$ (-)']


def text_color_for(rgba):
    """Black text on light cells, white text on dark cells."""
    r, g, b, _ = rgba
    return "white" if 0.299 * r + 0.587 * g + 0.114 * b < 0.5 else "black"


def add_table_column(ax, values, j, cmap, norm):
    """Shade one column of the table; the NaN summary row shows as white."""
    display = np.array(values, dtype=float)
    display[-1] = np.nan
    ax.imshow(display[:, None], cmap=cmap, norm=norm, aspect="auto",
              extent=[j - 0.5, j + 0.5, 0, len(values)], origin="lower")


def annotate_column(ax, values, j, cmap, norm, fmt):
    """Print every value; the last (summary) row is a signed relative change."""
    for i, val in enumerate(values):
        if i == len(values) - 1:
            color = "forestgreen" if val >= 0 else "darkred"
            label, fontsize = f"{val:+.1f} %", 16
        else:
            color = text_color_for(cmap(norm(val)))
            label, fontsize = fmt.format(val), 14
        ax.text(j, i + 0.5, label, ha="center", va="center", fontsize=fontsize, color=color)


def style_table_axis(ax, title):
    ax.set_title(title, fontsize=32, pad=24)
    ax.set_xlim(-0.5, len(column_labels) - 0.5)
    ax.set_xticks(np.arange(len(column_labels)))
    # Anchor the rotated labels at their right end so each one ends under its column.
    ax.set_xticklabels(column_labels, fontsize=20, rotation=30,
                       ha='right', rotation_mode='anchor')
    ax.tick_params(axis='both', which='both', length=0)
    ax.set_frame_on(False)
    ax.invert_yaxis()  # first method on top


def save(fig, stem, dpi):
    FIG_DIR.mkdir(exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(FIG_DIR / f'{stem}.{ext}', dpi=dpi)
    plt.close(fig)


def plot_speed():
    idx = [4, 5, 6, 7, OURS]  # guided generators + ours
    speed_values = 1 / np.array([results_inference[i] for i in idx])
    options_speed = [options[i] for i in idx]

    fig = plt.figure(figsize=(9, 5))
    ax = fig.add_subplot(1, 1, 1)
    # A list of labels gives every bar its own legend entry (no x tick labels needed).
    bars = ax.bar(np.arange(len(options_speed)), speed_values,
                  color=[colors[i] for i in idx], label=options_speed)
    ax.bar_label(bars, fmt='%.3f', padding=3, fontsize=16)
    ax.set_xlim([-1, len(options_speed)])
    ax.set_ylim([0, 2.2])  # headroom for the value labels
    ax.set_yticks(np.arange(0, 2.01, 0.5))
    ax.legend(loc='upper left', frameon=False, fontsize=16, ncol=1)
    ax.set_xticks([])
    ax.set_ylabel('Inference Throughput ' + r'$\uparrow$' + '\n(samples / ms)', fontsize=18)

    fig.tight_layout(pad=1)
    save(fig, 'results_comparison_speed', dpi=300)


def plot_optimization():
    fig = plt.figure(figsize=(20, 9))

    # --- Left: median change in property. Even columns = (+), odd = (-). ---
    ax = fig.add_subplot(1, 2, 1)
    improvements = np.stack([results_openvaccine_delta_pos, results_openvaccine_delta_neg,
                             results_zebrafish_delta_pos, results_zebrafish_delta_neg,
                             results_ribosome_delta_pos, results_ribosome_delta_neg], axis=1)
    direction = np.array([1, -1] * 3)  # +1: larger is better, -1: smaller is better
    baselines = improvements[:OURS]
    best = np.where(direction > 0, baselines.max(0), baselines.min(0))
    denom = np.where(best == 0, np.nan, np.abs(best))
    improvement_over_best = 100 * direction * (improvements[OURS] - best) / denom
    improvements = np.vstack([improvements, improvement_over_best])
    vmin, vmax = improvements[:-1].min(0), improvements[:-1].max(0)

    cmap_red = plt.cm.Reds.with_extremes(bad="white")
    cmap_blue = plt.cm.Blues_r.with_extremes(bad="white")
    for j in range(improvements.shape[1]):
        if direction[j] > 0:
            cmap, norm = cmap_red, mpl.colors.Normalize(vmin=0, vmax=vmax[j])
        else:
            cmap, norm = cmap_blue, mpl.colors.Normalize(vmin=vmin[j], vmax=0)
        add_table_column(ax, improvements[:, j], j, cmap, norm)
        annotate_column(ax, improvements[:, j], j, cmap, norm, "{:.2f}")
    ax.set_yticks(np.arange(len(options)) + 0.5)
    ax.set_yticklabels(options, rotation=0, fontsize=20, ha='right')
    ax.get_yticklabels()[OURS].set_fontsize(24)  # emphasise our method
    style_table_axis(ax, 'Median change in property')

    # --- Right: success rate (%), higher is better in every column. ---
    ax = fig.add_subplot(1, 2, 2)
    percentages = np.stack([results_openvaccine_pct_pos, results_openvaccine_pct_neg,
                            results_zebrafish_pct_pos, results_zebrafish_pct_neg,
                            results_ribosome_pct_pos, results_ribosome_pct_neg], axis=1)
    best = percentages[:OURS].max(0)
    pct_improvement_over_best = 100 * (percentages[OURS] - best) / best
    percentages = np.vstack([percentages, pct_improvement_over_best])
    vmin, vmax = percentages[:-1].min(0), percentages[:-1].max(0)
    for j in range(percentages.shape[1]):
        # Shade from 50 % (chance level) upwards; lower success rates stay white.
        norm = mpl.colors.Normalize(vmin=max(50, vmin[j]), vmax=vmax[j])
        add_table_column(ax, percentages[:, j], j, cmap_red, norm)
        annotate_column(ax, percentages[:, j], j, cmap_red, norm, "{:.1f} %")
    ax.set_yticks([])  # rows are named by the left panel
    style_table_axis(ax, 'Success rate')

    fig.tight_layout(pad=2)
    save(fig, 'results_comparison_optimization', dpi=300)


if __name__ == '__main__':
    # mathtext (no LaTeX install needed): sans for \mathit/\mathbf, monospace for \mathtt.
    plt.rcParams['mathtext.fontset'] = 'custom'
    plt.rcParams['mathtext.rm'] = 'sans'
    plt.rcParams['mathtext.it'] = 'sans:italic'
    plt.rcParams['mathtext.bf'] = 'sans:bold'
    plt.rcParams['mathtext.tt'] = 'monospace'
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans']
    plt.rcParams['font.size'] = 16
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.linewidth'] = 2
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['svg.fonttype'] = 'none'

    plot_speed()
    plot_optimization()
