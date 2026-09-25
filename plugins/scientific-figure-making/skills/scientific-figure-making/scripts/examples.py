"""Worked examples for pubfig. Each function is a complete recipe to copy from.

    python examples.py --out figures_demo

Data are synthetic placeholders; replace them with real results.
"""

from __future__ import annotations

import argparse

import numpy as np

from pubfig import (
    PALETTE, add_figure_legend, apply_publication_style, create_subplots, figsize,
    finalize_figure, label_panels, make_grouped_bar, make_heatmap, make_method_bars,
    make_trend, tint, tighten_ylim,
)

rng = np.random.default_rng(0)


def per_metric_bars(out):
    """Main-results figure: one panel per metric, one bar per method, shared legend on top."""
    methods = ["Baseline", "Method A", "Method B", "Ours"]
    colors = ["neutral", "red_2", "red_strong", "blue_main"]
    metrics = {"Accuracy": [0.71, 0.78, 0.81, 0.87],
               "F1": [0.64, 0.72, 0.74, 0.83],
               "AUROC": [0.80, 0.84, 0.86, 0.92]}
    fig, axes = create_subplots(1, 3, figsize=figsize("nature", "double", aspect=0.32))
    for ax, (metric, vals) in zip(axes, metrics.items()):
        sd = rng.uniform(0.01, 0.025, len(vals))
        make_method_bars(ax, vals, methods, errors=sd, colors=colors, title=metric,
                         annotate=True, fmt="{:.2f}")
        ax.set_ylim(0, 1.05)  # bars start at zero
    axes[0].set_ylabel("Score (mean ± SD, n = 5)")
    add_figure_legend(fig, axes[:1])
    label_panels(axes)
    finalize_figure(fig, f"{out}/per_metric_bars")


def ablation_bars(out):
    """Ablation: shades of one colour (tint, not alpha) + hatch for a sub-variant."""
    datasets = ["CIFAR-10", "CIFAR-100", "ImageNet"]
    variants = ["w/o A and B", "w/o B", "w/o A", "Full"]
    scores = [[88.1, 61.0, 70.2], [90.4, 64.3, 72.8], [91.0, 65.1, 73.5], [93.2, 68.7, 76.1]]
    colors = [tint("blue_secondary", a) for a in (0.25, 0.5, 0.5, 1.0)]
    hatches = [None, None, "///", None]
    fig, ax = create_subplots(figsize=figsize("nature", "single", aspect=0.75))
    make_grouped_bar(ax, datasets, scores, variants, colors=colors, hatches=hatches,
                     ylabel="Top-1 accuracy (%)")
    ax.set_ylim(0, 100)
    ax.legend(ncols=2, loc="upper center", bbox_to_anchor=(0.5, 1.28))
    finalize_figure(fig, f"{out}/ablation_bars")


def training_curves(out):
    """Trends with SD bands, markers + line styles so it survives grayscale."""
    epochs = np.arange(1, 51)
    series, bands = [], []
    for rate, top in ((6, 0.92), (9, 0.86), (12, 0.80)):
        runs = top * (1 - np.exp(-epochs / rate)) + rng.normal(0, 0.012, (5, len(epochs)))
        series.append(runs.mean(0))
        bands.append(runs.std(0))
    labels = ["Ours", "Method B", "Baseline"]
    colors = ["blue_main", "red_strong", "gray"]
    fig, axes = create_subplots(1, 2, figsize=figsize("icml", "double", aspect=0.36))
    make_trend(axes[0], epochs, series, labels, bands=bands, colors=colors,
               linestyles=["-", "--", ":"], xlabel="Epoch", ylabel="Validation accuracy")
    final = [s[-10:] for s in series]
    make_trend(axes[1], epochs[-10:], final, labels, colors=colors,
               linestyles=["-", "--", ":"], markers=["o", "s", "^"], markevery=3,
               xlabel="Epoch (last 10)")
    tighten_ylim(axes[1], final)  # fine for lines; never for bars
    add_figure_legend(fig, axes[:1])
    label_panels(axes)
    finalize_figure(fig, f"{out}/training_curves")


def correlation_heatmap(out):
    """Signed values -> diverging map centred on 0."""
    names = ["Age", "BMI", "Glucose", "Insulin", "HbA1c", "SBP"]
    latent = rng.normal(size=(200, 2))
    data = latent @ rng.normal(size=(2, len(names))) + rng.normal(0, 0.8, (200, len(names)))
    corr = np.corrcoef(data, rowvar=False)
    fig, ax = create_subplots(figsize=figsize("nature", "single", aspect=0.85))
    make_heatmap(ax, corr, names, names, center=0, vmin=-1, vmax=1,
                 cbar_label="Pearson r", annotate=True, fmt="{:.2f}")
    finalize_figure(fig, f"{out}/correlation_heatmap")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="figures_demo")
    args = parser.parse_args()
    apply_publication_style("paper")
    for recipe in (per_metric_bars, ablation_bars, training_curves, correlation_heatmap):
        recipe(args.out)
