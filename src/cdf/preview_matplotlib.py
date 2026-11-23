"""Optional matplotlib preview for Assignment 2.1."""

import matplotlib.pyplot as plt

from cdf.ripple_core import (
    Params,
    count_class_pixels,
    generate_ripple_field,
    get_tile_size,
)


def preview_ripple(params: Params) -> None:
    """Draw the classified floor and the placed rain drops."""
    if params.tile_columns < 1:
        raise ValueError("tile_columns must be at least 1.")
    if params.tile_rows < 1:
        raise ValueError("tile_rows must be at least 1.")

    result = generate_ripple_field(params)

    image = []
    for class_row in result.classes:
        image.append(list(class_row))

    figure, axis = plt.subplots(figsize=(10, 7))

    # 0 = dark, 1 = mid, 2 = light.
    image_plot = axis.imshow(
        image,
        origin="lower",
        extent=(0.0, params.width, 0.0, params.height),
        cmap="Greys",
        vmin=0,
        vmax=2,
        aspect="equal",
        interpolation="nearest",
    )

    for drop in result.drops:
        axis.scatter(
            drop.x,
            drop.y,
            s=35,
            c="red",
            edgecolors="white",
            linewidths=0.5,
            zorder=3,
        )

    tile_width, tile_height = get_tile_size(params)

    x_lines = []
    x = 0.0
    while x <= params.width:
        x_lines.append(x)
        x += tile_width

    y_lines = []
    y = 0.0
    while y <= params.height:
        y_lines.append(y)
        y += tile_height

    axis.vlines(
        x_lines,
        0.0,
        params.height,
        colors="black",
        linewidth=0.8,
        alpha=0.45,
        zorder=4,
    )
    axis.hlines(
        y_lines,
        0.0,
        params.width,
        colors="black",
        linewidth=0.8,
        alpha=0.45,
        zorder=4,
    )

    axis.set_title(
        "Frozen Rain-Wave Floor Pattern - {} x {} Tiles".format(
            params.tile_columns,
            params.tile_rows,
        )
    )
    axis.set_xlabel("Floor width [mm]")
    axis.set_ylabel("Floor height [mm]")
    axis.set_xticks([0, params.width / 2.0, params.width])
    axis.set_yticks([0, params.height / 2.0, params.height])

    dark, mid, light = count_class_pixels(result.classes)
    axis.text(
        0.02,
        0.98,
        "Drops: {}\nDark/Mid/Light: {}/{}/{}\nHash: {}".format(
            len(result.drops),
            dark,
            mid,
            light,
            result.hash[:12],
        ),
        transform=axis.transAxes,
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    color_bar = figure.colorbar(image_plot, ticks=[0, 1, 2])
    color_bar.ax.set_yticklabels(["Dark", "Mid", "Light"])
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    preview_ripple(Params())
