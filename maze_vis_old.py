"""
Deprecated compatibility shim for the legacy grid visualizer (`maze_vis_old.py`).

NOTE: Kept intentionally in the starter repository and scheduled for full removal
during Milestone 1 cleanup. Native GUI rendering has been replaced by the local
Chrome web visualizer in `maze_vis.py`.
"""

from __future__ import annotations

import warnings
from typing import Any, Sequence

from maze_vis import MazeGrid


def create_grid(
    schma: Sequence[Sequence[Any]],
    rows: int = 20,
    columns: int = 20,
    bg_colour: str = "#f0dfce",
    line_colour: str = "#1f2937",
    serve: bool = False,
    port: int = 8000,
) -> MazeGrid:
    """
    Deprecated wrapper around `maze_vis.MazeGrid`.
    Returns the `MazeGrid` instance (and serves on localhost if `serve=True`).
    """
    warnings.warn(
        "maze_vis_old.create_grid is deprecated and scheduled for removal in Milestone 1; "
        "use maze_vis.MazeGrid instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    grid = MazeGrid(
        schema=schma,
        rows=rows,
        columns=columns,
        bg_colour=bg_colour,
        line_colour=line_colour,
        title="Legacy Maze Grid (Deprecated Wrapper)",
    )
    if serve:
        grid.run(port=port)
    return grid


if __name__ == "__main__":
    sample_grid = create_grid(
        [
            ["0", "1", "0", "A", "C"],
            ["1", "0", "C", "0", "1"],
            ["A", "1", "0", "C", "0"],
            ["0", "C", "1", "1", "A"],
            ["C", "0", "A", "0", "1"],
        ],
        5,
        5,
        serve=True,
    )
