#!/usr/bin/env bash
set -e

# Resilient Search & Rescue (SAR) — Unified Offline Test Runner
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Detect working Python interpreter
PYTHON_EXEC=""
for candidate in "/usr/bin/python3" "python3" "python"; do
  if "$candidate" -c "import sys" >/dev/null 2>&1; then
    PYTHON_EXEC="$candidate"
    break
  fi
done

if [ -z "$PYTHON_EXEC" ]; then
  echo "[ERROR] No working Python interpreter found on PATH." >&2
  exit 1
fi

echo "======================================================="
echo "==> 0. Syntax & Bytecode Compilation Check..."
echo "======================================================="
"$PYTHON_EXEC" -m py_compile \
  maze.py maze_vis.py maze_vis_old.py maze-test.py agent.py \
  sar_swarm/__init__.py sar_swarm/models.py sar_swarm/vision_and_grid.py \
  sar_swarm/coordinator.py sar_swarm/agents.py sar_swarm/demo_sim.py \
  sar_swarm/tests/test_sar.py
echo "[PASS] All Python modules compiled cleanly."

echo ""
echo "======================================================="
echo "==> 1. Running Core SAR Unit & Integration Test Suite via $PYTHON_EXEC..."
echo "======================================================="
"$PYTHON_EXEC" -m sar_swarm.tests.test_sar

echo ""
echo "======================================================="
echo "==> 2. Verifying Agent & Coordinator Contracts..."
echo "======================================================="
"$PYTHON_EXEC" -c '
from agent import RescueAgent, Link
from sar_swarm import Coordinator, create_sar_team, AgentA1, AgentA2, AgentA3

maze = [
    [0, 1, 0, 0, 0],
    [0, 1, 0, 1, 0],
    [0, 0, 0, 1, 0],
    [1, 1, 0, 0, 0],
]
agent = RescueAgent("A1", maze, (0, 0))
assert agent.connected
assert (0, 0) in agent.visible_cells()
agent.observe(exits=[(0, 0)], people=[(2, 4)])
msgs = agent.exchange()
assert len(msgs) >= 1
print("[PASS] RescueAgent contract verified.")

coord, team = create_sar_team(maze, total_targets_goal=1, entrances=[(0, 0)])
assert isinstance(team["A1"], AgentA1)
assert isinstance(team["A2"], AgentA2)
assert isinstance(team["A3"], AgentA3)
print("[PASS] Coordinator & 3-Agent team factory verified.")
'

echo ""
echo "======================================================="
echo "==> 3. Verifying Deterministic Procedural Maze Generation..."
echo "======================================================="
"$PYTHON_EXEC" -c '
from maze import Maze
m = Maze(12, seed=42)
m.gen_wounded(3)
m.seal()
m.poke(2, 2)
assert len(m.maze) == 14
assert len(m.maze[0]) == 14
assert len(m.targets) == 3
print("[PASS] Procedural Maze generator verified.")
'

echo ""
echo "======================================================="
echo "==> 4. Verifying Headless Multi-Agent Simulation & Web Replay..."
echo "======================================================="
"$PYTHON_EXEC" -c '
from sar_swarm.demo_sim import run_episode, SAMPLE_FLOOR_PLAN, SAMPLE_TARGETS
from maze_vis import build_viewer_html

# Test under 100% comms
res_online = run_episode(SAMPLE_FLOOR_PLAN, SAMPLE_TARGETS, lambda a, p, s, e: True, max_steps=150, record_frames=True)
assert res_online["actual_rescued_count"] == len(SAMPLE_TARGETS)
assert len(res_online["frames"]) > 1
print("[PASS] Online simulation episode & replay capture verified.")

# Test under sudden blackout
res_offline = run_episode(SAMPLE_FLOOR_PLAN, SAMPLE_TARGETS, lambda a, p, s, e: (p in e) or (s < 5), max_steps=180, record_frames=True)
assert res_offline["actual_rescued_count"] == len(SAMPLE_TARGETS)
html = build_viewer_html([{"name": "Blackout", "summary": res_offline, "frames": res_offline["frames"]}])
assert "<canvas" in html
print("[PASS] Sudden comms blackout simulation & offline Chrome HTML verified.")
'

echo ""
echo "======================================================="
echo "==> All Resilient SAR verifications passed successfully!"
echo "======================================================="
