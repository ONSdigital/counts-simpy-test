"""Display England and Wales local authority boundaries using VS Code's Run button."""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt


def main():
    shapefile = Path(__file__).resolve().parent / "LA_maps" / "LAD_MAY_2025_UK_BUC.shp"
    boundaries = gpd.read_file(shapefile)
    boundaries = boundaries.loc[boundaries["LAD25CD"].str.startswith(("E", "W"), na=False)]

    figure, axis = plt.subplots(figsize=(10, 12))
    boundaries.plot(
        ax=axis,
        facecolor="#d8e8df",
        edgecolor="#36564a",
        linewidth=0.15,
        aspect="equal",
    )
    axis.set_title("May 2025 Local Authority Districts\nEngland and Wales")
    axis.set_axis_off()
    figure.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()