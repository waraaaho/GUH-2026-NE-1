"""
Integration Harness & Demonstration for the Coordinator and 3 Agents (A1, A2, A3).

Demonstrates:
1. Full 1-to-1 Comms
2. Sudden Signal Cutoff (Signal stops suddenly mid-mission; always ON outside the maze)
3. Heavy Door 'D' requiring 2 agents to unblock + Offline Ground Markers ('I' & 'O')

Supports both headless CLI summaries and local Chrome step-through replay via
`python3 -m sar_swarm.demo_sim --serve --port 8000`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

try:
    from .agents import BaseAgent, create_sar_team
    from .coordinator import Coordinator
    from .models import Coord, GroundMarker, StepDecision
    from .vision_and_grid import extract_doors_from_floor_plan, to_visualization_schema
except ImportError:
    from agents import BaseAgent, create_sar_team
    from coordinator import Coordinator
    from models import Coord, GroundMarker, StepDecision
    from vision_and_grid import extract_doors_from_floor_plan, to_visualization_schema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maze_vis import build_viewer_html, serve_replay_app

DEFAULT_SAMPLE_FLOOR_PLAN: List[List[Any]] = [
    [1, 1, 1, 1, 1, "A1", "A2", "A3", 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1, 0,    0,    0,    1, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 0, 1, 0,    1,    0,    1, 0, 1, 1, 1, 0, 1],
    [1, 0, 1, 0, 0, 0,    1,    0,    0, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 1, 1, 0,    1,    1,    1, 1, 1, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0,    0,    0,    0, 0, 1, 0, 0, 0, 1],
    [1, 1, 1, 0, 1, 1,    1,    "D",  1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 0,    0,    0,    1, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 0, 1, 0,    1,    1,    1, 1, 1, 0, 1, 0, 1],
    [1, 0, 1, 0, 0, 0,    0,    0,    0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1,    1,    1,    1, 1, 1, 1, 1, 1, 1],
]

DEFAULT_SAMPLE_TARGETS: Dict[str, Coord] = {
    "P1": (1, 1),
    "P2": (7, 5),
    "P3": (1, 13),
    "P4": (9, 13),
}

SAMPLE_FLOOR_PLAN = DEFAULT_SAMPLE_FLOOR_PLAN
SAMPLE_TARGETS = DEFAULT_SAMPLE_TARGETS


def run_episode(
    floor_plan: Sequence[Sequence[Any]],
    targets: Dict[str, Coord],
    comm_policy: Callable[[str, Coord, int, List[Coord]], bool],
    max_steps: int = 220,
    verbose: bool = False,
    grid_ui: Any = None,
    maze_obj: Any = None,
    record_frames: bool = False,
) -> Dict[str, Any]:
    """
    Runs a full Search & Rescue simulation episode with:
      - 1 Coordinator (outside the maze)
      - 3 Agents (A1, A2, A3) going in and out of the maze multiple times
      - Heavy Doors 'D' (require 2 agents adjacent to unlock)
      - Offline Ground Markers 'I' (invite to door 'D') and 'O' (dead end ahead)
    """
    active_targets: Dict[str, Coord] = dict(targets)
    closed_doors: Set[Coord] = extract_doors_from_floor_plan(floor_plan)
    ground_markers: Dict[Coord, GroundMarker] = {}
    rescued_targets: List[str] = []

    coordinator, agents = create_sar_team(
        floor_plan=floor_plan,
        total_targets_goal=len(targets),
    )

    step_history: List[Dict[str, StepDecision]] = []
    markers_dropped_history: List[GroundMarker] = []
    doors_unlocked_history: List[Coord] = []
    replay_frames: List[Dict[str, Any]] = []

    if record_frames:
        initial_schema = to_visualization_schema(
            grid=coordinator.grid,
            agent_positions={aid: ag.position for aid, ag in agents.items()},
            target_positions=active_targets,
            closed_doors=closed_doors,
            ground_markers=ground_markers,
        )
        replay_frames.append(
            {
                "step": 0,
                "schema": initial_schema,
                "meta": {
                    "rescued": list(rescued_targets),
                    "closed_doors": [list(d) for d in sorted(closed_doors)],
                    "agents": {
                        aid: {"pos": list(ag.position), "mode": ag.mode.value}
                        for aid, ag in agents.items()
                    },
                },
            }
        )

    for step in range(1, max_steps + 1):
        all_positions = {aid: ag.position for aid, ag in agents.items()}
        step_decisions: Dict[str, StepDecision] = {}

        for aid in ("A1", "A2", "A3"):
            agent = agents[aid]

            decision = agent.step(
                coordinator=coordinator,
                comm_available=lambda pos, _aid=aid, _s=step: comm_policy(
                    _aid, pos, _s, coordinator.entrances
                ),
                active_targets=active_targets,
                all_agent_positions=all_positions,
                closed_doors=closed_doors,
                ground_markers=ground_markers,
            )
            step_decisions[aid] = decision
            all_positions[aid] = decision.next_pos
            if maze_obj is not None and hasattr(maze_obj, "clear_agent"):
                maze_obj.clear_agent(aid, decision.next_pos)

            if decision.dropped_marker is not None:
                markers_dropped_history.append(decision.dropped_marker)

            if (
                decision.unlocked_door_pos is not None
                and decision.unlocked_door_pos not in doors_unlocked_history
            ):
                doors_unlocked_history.append(decision.unlocked_door_pos)

            if (
                decision.picked_up_target_id
                and decision.picked_up_target_id in active_targets
            ):
                del active_targets[decision.picked_up_target_id]

            if (
                decision.rescued_target_id
                and decision.rescued_target_id not in rescued_targets
            ):
                rescued_targets.append(decision.rescued_target_id)

        if grid_ui is not None and maze_obj is not None:
            grid_ui.update(maze_obj.maze)

        if record_frames:
            frame_schema = to_visualization_schema(
                grid=coordinator.grid,
                agent_positions={aid: ag.position for aid, ag in agents.items()},
                target_positions=active_targets,
                closed_doors=closed_doors,
                ground_markers=ground_markers,
            )
            replay_frames.append(
                {
                    "step": step,
                    "schema": frame_schema,
                    "meta": {
                        "rescued": list(rescued_targets),
                        "closed_doors": [list(d) for d in sorted(closed_doors)],
                        "markers": len(ground_markers),
                        "agents": {
                            aid: {
                                "pos": list(step_decisions[aid].next_pos),
                                "mode": step_decisions[aid].mode.value,
                                "synced": step_decisions[aid].synced_with_coordinator,
                                "carrying": step_decisions[aid].carrying_target_id,
                            }
                            for aid in ("A1", "A2", "A3")
                        },
                    },
                }
            )

        step_history.append(step_decisions)

        if len(rescued_targets) >= len(targets):
            break

    summary = coordinator.get_summary()
    summary["actual_rescued_count"] = len(rescued_targets)
    summary["steps_taken"] = len(step_history)
    summary["doors_unlocked"] = [list(d) for d in doors_unlocked_history]
    summary["markers_dropped_count"] = len(markers_dropped_history)
    summary["total_trips_completed"] = sum(ag.trips_completed for ag in agents.values())
    if record_frames:
        summary["frames"] = replay_frames
    return summary


def build_default_scenarios(record_frames: bool = False) -> List[Dict[str, Any]]:
    scenarios = [
        (
            "1. Full 1-to-1 Comms (Always Connected)",
            lambda aid, pos, step, entrances: True,
        ),
        (
            "2. Sudden Signal Cutoff at Step 8 (Always ON Outside at Entrance)",
            lambda aid, pos, step, entrances: (pos in entrances) or (step < 8),
        ),
        (
            "3. Total Interior Blackout (Only Entrance Has Signal + Offline 'I'/'O' Markers)",
            lambda aid, pos, step, entrances: pos in entrances,
        ),
    ]

    results: List[Dict[str, Any]] = []
    for name, policy in scenarios:
        res = run_episode(
            floor_plan=SAMPLE_FLOOR_PLAN,
            targets=SAMPLE_TARGETS,
            comm_policy=policy,
            max_steps=220,
            verbose=False,
            record_frames=record_frames,
        )
        frames = res.pop("frames", [])
        results.append({"name": name, "summary": res, "frames": frames})
    return results


def main(
    serve: bool = False,
    port: int = 8000,
    export_html: Optional[str] = None,
) -> None:
    print("=" * 76)
    print("RESILIENT SAR — COORDINATOR + 3 AGENTS + DOORS ('D') + MARKERS ('I','O')")
    print("=" * 76)

    need_frames = serve or bool(export_html)
    scenario_runs = build_default_scenarios(record_frames=need_frames)

    for entry in scenario_runs:
        name = entry["name"]
        res = entry["summary"]
        print(f"\nScenario: {name}")
        print(
            f"  Targets Rescued   : {res['actual_rescued_count']} / {res['targets_goal']}"
        )
        print(f"  Steps Taken       : {res['steps_taken']}")
        print(f"  Doors 'D' Opened  : {res['doors_unlocked']}")
        print(f"  Markers ('I'/'O') : {res['markers_dropped_count']}")
        print(f"  Multi-Exit Trips  : {res['total_trips_completed']}")
        print(f"  1-to-1 Syncs      : {res['sync_counts']}")

    if export_html:
        out_path = Path(export_html)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(build_viewer_html(scenario_runs), encoding="utf-8")
        print(f"\nExported offline Chrome replay to: {out_path}")

    if serve:
        serve_replay_app(scenario_runs, host="127.0.0.1", port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resilient SAR 3-scenario demo & Chrome replay.")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start local offline HTTP server for Chrome replay inspection.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for local HTTP replay server (default: 8000).",
    )
    parser.add_argument(
        "--export-html",
        type=str,
        default=None,
        help="Optional path to write standalone offline HTML replay.",
    )
    cli_args = parser.parse_args()
    main(serve=cli_args.serve, port=cli_args.port, export_html=cli_args.export_html)
