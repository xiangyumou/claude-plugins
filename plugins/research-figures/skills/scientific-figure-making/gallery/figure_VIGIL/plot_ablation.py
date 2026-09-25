"""Ablation curves for VIGIL (vision-grounded preference optimisation for VLMs).

Three line panels in one wide row, all on POPE_Adv (higher is better):
  (1) score vs. fraction of post-training data, with an "SFT only" reference line
      and a dotted guide showing that VIGIL with 25% of the data already beats
      both baselines trained on 100%;
  (2) score vs. the DPO temperature beta for DPO / DA-DPO / VIGIL;
  (3) VIGIL's own weight lambda, with a twin y-axis: POPE_Adv (light, left) and
      MathVista (dark, right), plus the mean of the two metrics printed on top.

Techniques worth borrowing:
  - categorical x positions (np.arange) with the real values as tick labels, so
    unevenly spaced settings (0.05, 0.1, 0.2, 0.5) are drawn evenly;
  - a twin axis whose two series share one hue and differ in lightness, with the
    axis label coloured to match; both series go into ONE legend;
  - a horizontal guide line + short text label to make a claim readable at a glance.

Run:  python plot_ablation.py   ->  figures/ablation_curves.{png,pdf}
"""
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

FIG_DIR = Path(__file__).resolve().parent / 'figures'

data_ablation = {
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
    'beta': [0.05, 0.1, 0.2, 0.5],
    'lambda': [0.1, 0.5, 1.0, 2.0],
    'data_fraction': [0.1, 0.25, 0.5, 1.0],
    'results': {
        'SFT': 82.1,  # POPE_Adv of the SFT-only starting model.
        # Shape (n_methods, n_beta): 3 methods x 4 beta values.
        'beta': np.array([
            [79.5, 82.8, 81.0, 76.2],
            [83.2, 84.2, 83.5, 81.0],
            [86.8, 86.9, 86.5, 85.8],
        ]),
        # Our method only. Rows: POPE_Adv, MathVista; columns: lambda values.
        'lambda': np.array([
            [84.5, 86.1, 86.9, 87.2],  # POPE_Adv
            [49.8, 49.6, 49.5, 48.8],  # MathVista
        ]),
        # Shape (n_methods, n_data_fraction).
        'data_fraction': np.array([
            [82.78, 83.19, 85.05, 85.67],
            [84.04, 85.46, 87.07, 87.81],
            [86.69, 88.18, 89.17, 89.82],
        ])
    }
}

POPE_LABEL = r'POPE$_\mathrm{Adv}\,\uparrow$'
MATHVISTA_LABEL = r'MathVista$\,\uparrow$'


def plot_curves(data_ablation):
    """Panels: data fraction | beta (3 methods) | lambda (VIGIL, twin y-axis)."""
    methods = data_ablation['methods']
    colors = data_ablation['colors']
    results = data_ablation['results']

    fig, axes = plt.subplots(1, 3, figsize=(27, 6), gridspec_kw={'width_ratios': [1.1, 1, 1]})

    # ---- Panel 1: fraction of post-training data ----------------------------
    ax = axes[0]
    data_fraction_vals = np.asarray(data_ablation['data_fraction'])
    results_data_fraction = results['data_fraction']
    x_pos = np.arange(len(data_fraction_vals))
    ax.axhline(results['SFT'], color='black', alpha=0.3, linewidth=4, linestyle='--', label='SFT only')
    # Guide: VIGIL with 25% of the data vs. the baselines with 100%.
    y_ours_25 = results_data_fraction[-1][1]
    ax.plot([x_pos[0] - 0.1, x_pos[-1] + 0.1], [y_ours_25, y_ours_25], color=colors[-1], linewidth=3, linestyle=':')
    ax.text(x_pos[0] - 0.45, y_ours_25 + 0.25, 'VIGIL w/ 25% data', color=colors[-1],
            ha='left', va='bottom', fontsize=20)
    for m, (method, color) in enumerate(zip(methods, colors)):
        ax.plot(x_pos, results_data_fraction[m], color=color, linewidth=3, marker='o', markersize=10, label=method)

    ax.set_xlabel('Fraction of data used for post-training', fontsize=28, labelpad=18)
    ax.set_xlim(x_pos[0] - 0.5, x_pos[-1] + 0.4)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f'{item:.0%}' for item in data_fraction_vals])
    ax.set_ylabel(POPE_LABEL, fontsize=28, labelpad=12)
    ax.set_yticks([78, 82, 86, 90])
    ax.tick_params(labelsize=24, length=8, width=1.5)
    ax.legend(fontsize=24, loc='lower center', ncols=2, frameon=False)

    # ---- Panel 2: hyperparameter beta ---------------------------------------
    ax = axes[1]
    beta_vals = data_ablation['beta']
    x_pos = np.arange(len(beta_vals))
    for m, (method, color) in enumerate(zip(methods, colors)):
        ax.plot(x_pos, results['beta'][m], color=color, linewidth=3, marker='o', markersize=10, label=method)

    ax.set_xlabel(r'Hyperparameter $\beta$', fontsize=28, labelpad=18)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([str(b) for b in beta_vals])
    ax.set_ylabel(POPE_LABEL, fontsize=28, labelpad=12)
    ax.set_ylim(75, 88)
    ax.set_yticks([75, 79, 83, 87])  # evenly spaced (step 4, as in panel 1)
    ax.tick_params(labelsize=24, length=8, width=1.5)
    # Shifted left of centre so it sits under the curves, clear of DPO's drop at beta = 0.5.
    ax.legend(fontsize=24, loc='lower center', bbox_to_anchor=(0.42, 0.0), frameon=False)

    # ---- Panel 3: hyperparameter lambda, two metrics on twin axes -----------
    ax = axes[2]
    lambda_vals = data_ablation['lambda']
    results_lambda = results['lambda']
    assert len(results_lambda) == 2
    x_pos = np.arange(len(lambda_vals))
    # Same hue for both metrics; the light (alpha 0.4) one belongs to the left axis.
    line_pope, = ax.plot(x_pos, results_lambda[0], color=colors[-1], linewidth=3, marker='o', markersize=10,
                         alpha=0.4, label=r'POPE$_\mathrm{Adv}$ (left)')
    ax.set_xlabel(r'Hyperparameter $\lambda$', fontsize=28, labelpad=18)
    ax.set_xticks(x_pos)
    ax.set_xlim(x_pos[0] - 0.5, x_pos[-1] + 0.5)
    ax.set_xticklabels([str(b) for b in lambda_vals])
    ax.set_yticks([84, 85, 86, 87, 88])
    ax.set_ylabel(POPE_LABEL, fontsize=28, labelpad=12, color=colors[-1], alpha=0.4)
    ax.tick_params(labelsize=24, length=8, width=1.5)

    ax2 = ax.twinx()
    ax2.spines['right'].set_visible(True)
    line_mv, = ax2.plot(x_pos, results_lambda[1], color=colors[-1], linewidth=3, marker='o', markersize=10,
                        label='MathVista (right)')
    ax2.set_ylabel(MATHVISTA_LABEL, fontsize=28, labelpad=36, rotation=270, color=colors[-1])
    ax2.set_yticks([48, 48.5, 49, 49.5, 50])
    ax2.tick_params(labelsize=24, length=8, width=1.5)
    # One legend for both axes (drawn on the top-most axes so no line covers it).
    ax2.legend(handles=[line_pope, line_mv], fontsize=24, loc='lower center', frameon=False)

    # Mean of the two metrics at each lambda, printed along the top of the panel.
    y_top = ax.get_ylim()[1] - 0.2
    for i in range(len(x_pos)):
        avg = results_lambda[:, i].mean()
        ax.text(x_pos[i], y_top, f'Mean = {avg:.1f}', ha='center', va='bottom', fontsize=18)

    fig.tight_layout(pad=0.5)
    fig.subplots_adjust(wspace=0.3)
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / 'ablation_curves.png', dpi=300)
    fig.savefig(FIG_DIR / 'ablation_curves.pdf')
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

    plot_curves(data_ablation)
