"""
Generate a procedural maze and inspect it via the local Chrome web viewer
(or export a standalone offline HTML snapshot with `--export`).
"""

from __future__ import annotations

import argparse

from maze import Maze
from maze_vis import MazeGrid


def main() -> None:
    parser = argparse.ArgumentParser(description="Procedural maze web viewer demo.")
    parser.add_argument("--size", type=int, default=16, help="Inner maze dimension.")
    parser.add_argument("--wounded", type=int, default=10, help="Number of targets.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic RNG seed.")
    parser.add_argument("--port", type=int, default=8000, help="Local HTTP server port.")
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Optional path to export offline HTML instead of starting the HTTP server.",
    )
    args = parser.parse_args()

    my_maze = Maze(args.size, seed=args.seed)
    my_maze.gen_wounded(args.wounded)
    my_maze.seal()
    my_maze.poke(3, 3)

    my_grid = MazeGrid(
        schema=my_maze.maze,
        rows=my_maze.n,
        columns=my_maze.n,
        title=f"Procedural Maze ({args.size}x{args.size}, seed={args.seed})",
    )

    if args.export:
        out = my_grid.export_html(args.export)
        print(f"Exported offline HTML maze preview to {out}")
    else:
        my_grid.run(port=args.port)


if __name__ == "__main__":
    main()
