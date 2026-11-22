# Resilient Multi-Agent Search & Rescue (SAR)

> *"Actors work better together — Design a system where multiple agents keep working toward a shared goal, even when communication fails."*

An offline, deterministic multi-agent **Search & Rescue (SAR)** simulation engine, decentralized coordination protocol, and local Chrome replay workbench. Multiple autonomous field agents (`A1`, `A2`, `A3`, scaling to $K$-agent teams) explore occluded hazardous mazes with cooperative multi-agent heavy doors (`D`), sudden interior communication blackouts, and stigmergic ground markers (`I` and `O`).

> **Scope Note:** All planning, raycasting, frontier allocation, CRDT state reconciliation, and coordination heuristics are **100% classical deterministic algorithms** (zero AI/ML model training, evaluation, or inference). All floor plans, targets, and telemetry are **100% synthetic**.

---

## 1. Workspace Tier & Environment Fit

- **Workspace Tier:** `Desktop Workspace` (native Linux x86-64, 4 CPU cores, 16 GB RAM, 100% offline).
- **Stack:** Pure Python 3 standard library (`http.server`, `json`, `collections`, `dataclasses`, `sqlite3` module for upcoming checkpointing) + zero-CDN HTML5 Canvas web UI viewed in bundled Chrome.
- **Zero External Dependencies / Services:** No internet calls, no external CDNs or web fonts, no Docker, no GPU, no sound, no native desktop GUI toolkits, and no `[code workspace only]` services.
- **Browser Testing Note:** If Playwright E2E checks are added in Milestone 5, point Playwright at the desktop's bundled Chrome (`CHROME_PATH` / `executable_path`) without downloading Chromium.

---

## 2. Architecture & Maze Elements

| Path | Role |
|---|---|
| `sar_swarm/models.py` | Domain types (`Coord`, `GroundMarker`, `TargetRecord`, `VisibleObservation`, `AgentReport`, `CoordinatorDirective`, `StepDecision`). |
| `sar_swarm/vision_and_grid.py` | Floor-plan parser, 5×5 occlusion raycasting, BFS navigation, dead-end branch detection, and 3-sector spatial partitioning. |
| `sar_swarm/coordinator.py` | Outside base-station Coordinator (`C`): 1-to-1 sync, monotonic target merge, 2-agent door pairing, and dark-agent rebalancing. |
| `sar_swarm/agents.py` | Independent agent FSMs (`AgentA1` Deep-Vanguard, `AgentA2` Recon-Scout, `AgentA3` Support/Relay Specialist) + stigmergic `'I'`/`'O'` ground markers. |
| `sar_swarm/demo_sim.py` | Headless simulation runner, 3-scenario comparison harness, and replay frame recorder (`--serve` / `--export-html`). |
| `agent.py` | Alternate `RescueAgent` + `Link` API (scheduled for unification with `sar_swarm/agents.py` in Milestone 2). |
| `maze.py` | Procedural maze generator (`DFS` implemented with optional RNG `seed`; `ITER_STACK` and `KRUSKALS` reserved for Milestone 1). |
| `maze_vis.py` | Offline local HTTP server + self-contained HTML5 Canvas step-through replay viewer (`http://127.0.0.1:8000` in Chrome). |
| `maze_vis_old.py` | Deprecated compatibility shim delegating to `maze_vis.MazeGrid` (**scheduled for removal in Milestone 1**). |
| `scripts/serve_viewer.sh` | One-command restartable launcher for the local Chrome replay workbench. |
| `run_tests.sh` | Unified offline test runner (`py_compile`, unit/integration suite, contracts, seeded maze, headless replay verification). |

### Maze Symbols
- **`0`**: Walkable corridor/room tile.
- **`1`**: Impassable wall (blocks movement and 5×5 line-of-sight behind it).
- **`A1`, `A2`, `A3`**: Autonomous rescue agents (capable of multiple entry/exit trips).
- **`P` / `C`**: Trapped survivor (`P` in `sar_swarm`, `C` in `maze.py`) to locate and escort to the entrance.
- **`D`**: Heavy door blocking movement and sight until **2 agents** stand adjacent simultaneously (`D` -> `0`).
- **`I`**: Offline invite ground marker pointing teammates to a closed door `D`.
- **`O`**: Offline dead-end ground marker signaling that the branch beyond is fully cleared.

---

## 3. Quickstart, Testing & Restarting After Session Pauses

### 1. Run Full Offline Baseline Verification
Zero external packages required:
```bash
./run_tests.sh
```
Or run individual checks:
```bash
python3 -m sar_swarm.tests.test_sar
python3 -m sar_swarm.demo_sim
```

### 2. "See It" — Launch / Restart the Local Chrome Replay Workbench
Background processes pause between workspace turns; restart cleanly with one command:
```bash
./scripts/serve_viewer.sh 8000
# Open http://127.0.0.1:8000 in Chrome
```
To export a standalone offline HTML replay or procedural maze preview without starting a server:
```bash
python3 -m sar_swarm.demo_sim --export-html replay_out/demo_replay.html
python3 maze-test.py --size 16 --wounded 8 --seed 42 --export replay_out/maze_preview.html
```

---

## 4. Objective "Done When" Success Bar (Target End State)

All verification criteria run 100% offline within 4 CPU cores, 16 GB RAM, and ≤ 20 minutes per command:

1. **Multi-Seed Procedural Corpus & Zero Invariant Violations:** 100% rescue completion across **200 seeded procedural mazes** (spanning `DFS`, `ITER_STACK`, and `KRUSKALS` topologies, 15×15 to 41×41, with 1–5 heavy doors) under full comms, sudden blackout, and intermittent packet-loss regimes with **0 vertex collisions, 0 edge-swap collisions, and 0 wall/closed-door penetrations**.
2. **Deterministic Replay & Crash Recovery:** Repeat runs with identical seeds produce **byte-identical SHA-256 replay checksums**; SQLite WAL checkpoint/resume passes **100 forced `kill -9` mid-episode restarts** with 0 lost rescued targets or corrupted journal state (`PRAGMA integrity_check`).
3. **CRDT State-Merge & Adversarial Comms Convergence:** Under simulated wall-attenuated radio zones, dropped packets, and out-of-order 1-to-1 syncs, decentralized belief states converge with **0 duplicate target rescues** and total step count stays within **1.35× of the full-comms oracle baseline** on the 200-maze suite.
4. **Performance Budget:** Complete 200-maze headless benchmark finishes in **≤ 120 seconds** on 4 CPU cores with peak memory **< 1 GB** and mean step decision latency **< 5 ms/step** for up to $K = 12$ concurrent agents.
5. **Chrome Workbench Verification:** `http://127.0.0.1:8000` renders multi-scenario replays, side-by-side policy diffs, coverage heatmaps, and blackout timelines cleanly in bundled Chrome with zero network requests and passing automated headless verification.

---

## 5. Multi-Session Milestone Roadmap (Planned Work Ahead)

The current repository provides the working 3-agent offline baseline and minimal Chrome replay shell. Substantial engineering work remains ahead across workspace sessions:

- **Milestone 1 — Legacy Cleanup & Multi-Algorithm Procedural Benchmark Corpus:**
  - Remove deprecated `maze_vis_old.py` and dead legacy scaffolding.
  - Implement `ITER_STACK` and `KRUSKALS` generators in `maze.py` plus multi-room, corridor-chokepoint, and multi-door (`D`) placement with guaranteed solvability checks.
  - Build a deterministic 200-maze seeded benchmark generator & verifier (`python3 -m sar_swarm.bench --verify-corpus`).
- **Milestone 2 — Scalable $K$-Agent Collision-Free MAPF & Unified Agent Engine:**
  - Consolidate `agent.py` (`RescueAgent`) and `sar_swarm/agents.py` (`BaseAgent`) into one clean architecture supporting configurable $K \in [3, 16]$ agents.
  - Implement conflict-free movement arbitration (reservation table / prioritized planning / deadlock breaking) eliminating same-cell overlaps and head-on edge swaps.
- **Milestone 3 — Realistic Radio-Propagation, Adversarial Faults & Formal CRDT Sync:**
  - Model wall-attenuated signal strength, probabilistic packet loss, delayed/out-of-order coordinator uplinks, and peer-to-peer short-range mesh handoffs.
  - Harden monotonic CRDT target/door/coverage merging with randomized fuzz testing across 10,000 out-of-order sync permutations.
- **Milestone 4 — Dynamic Hazards & Crash-Safe SQLite WAL Checkpointing:**
  - Add dynamic environmental hazards (spreading smoke/occlusion, collapsing corridors, 2- and 3-agent cooperative doors) with deterministic re-planning.
  - Persist simulation snapshots and event logs to Python stdlib `sqlite3` (WAL mode) with a `kill -9` mid-run crash-recovery and SHA-256 replay-determinism suite.
- **Milestone 5 — Full Chrome Analytics Workbench & Quantitative Benchmark Gate:**
  - Upgrade the `http://127.0.0.1:8000` Chrome dashboard with 5×5 sight-cone overlays, coverage heatmaps, blackout timeline strips, and side-by-side policy comparisons.
  - Run the full 200-maze benchmark and bundled-Chrome verification suite (`CHROME_PATH`) to sign off every `"Done when"` criterion.

---

## 6. License & Ownership

Licensed under the **Apache License, Version 2.0** (see [LICENSE](LICENSE)). Original codebase owned and maintained by the repository author, adapted for 100% offline Linux Desktop Workspace execution.
