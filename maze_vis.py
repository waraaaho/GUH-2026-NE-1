"""
Local Chrome Web Visualizer & Step-Through Replay Server for Resilient SAR.

Zero external dependencies (pure Python 3 stdlib `http.server` + self-contained
offline HTML5 Canvas UI with zero external CDNs or fonts). Replaces legacy
native desktop GUI rendering so the simulation can be inspected directly at
http://127.0.0.1:8000 in Chrome on a Linux desktop workspace.
"""

from __future__ import annotations

import copy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _normalize_schema(schema: Sequence[Sequence[Any]]) -> List[List[str]]:
    return [[str(cell) for cell in row] for row in schema]


def build_viewer_html(
    scenarios: Sequence[Dict[str, Any]],
    title: str = "Resilient SAR — Local Chrome Replay Workbench",
    bg_colour: str = "#f0dfce",
    line_colour: str = "#1f2937",
) -> str:
    """Builds a self-contained, 100% offline HTML5 Canvas replay page."""
    payload_json = json.dumps(
        {
            "title": title,
            "bg_colour": bg_colour,
            "line_colour": line_colour,
            "scenarios": list(scenarios),
        }
    ).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #1e293b;
      --border: #334155;
      --text: #f1f5f9;
      --muted: #94a3b8;
      --accent: #38bdf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      background: var(--bg);
      color: var(--text);
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 100vh;
    }}
    header {{
      padding: 12px 20px;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: center;
      gap: 12px;
    }}
    header h1 {{
      margin: 0;
      font-size: 16px;
      letter-spacing: 0.02em;
    }}
    .controls {{
      display: grid;
      grid-auto-flow: column;
      align-items: center;
      gap: 8px;
    }}
    button, select {{
      background: #0f172a;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 10px;
      font-family: inherit;
      font-size: 13px;
      cursor: pointer;
    }}
    button:hover {{ border-color: var(--accent); }}
    main {{
      display: grid;
      grid-template-columns: minmax(320px, 1fr) 340px;
      gap: 16px;
      padding: 16px 20px;
    }}
    @media (max-width: 960px) {{
      header {{ grid-template-columns: 1fr; }}
      main {{ grid-template-columns: 1fr; }}
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
      display: grid;
      align-content: start;
      gap: 12px;
    }}
    .canvas-wrap {{
      display: grid;
      place-items: center;
      background: #0b1220;
      border-radius: 6px;
      padding: 12px;
      overflow: auto;
    }}
    canvas {{
      max-width: 100%;
      height: auto;
      border: 1px solid var(--border);
      border-radius: 4px;
    }}
    .scrubber {{
      display: grid;
      grid-template-columns: auto 1fr;
      align-items: center;
      gap: 10px;
    }}
    .scrubber input[type="range"] {{ width: 100%; }}
    .legend {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 6px;
      font-size: 12px;
    }}
    .legend-item {{
      display: grid;
      grid-template-columns: 14px 1fr;
      align-items: center;
      gap: 6px;
    }}
    .swatch {{
      width: 14px;
      height: 14px;
      border-radius: 3px;
      border: 1px solid #0f172a;
      display: inline-block;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      font-size: 12px;
    }}
    .metric-box {{
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px;
    }}
    .metric-label {{ color: var(--muted); font-size: 11px; }}
    .metric-val {{ font-size: 15px; font-weight: 700; margin-top: 2px; }}
    pre {{
      margin: 0;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px;
      font-size: 12px;
      white-space: pre-wrap;
      max-height: 300px;
      overflow-y: auto;
    }}
  </style>
</head>
<body>
  <header>
    <h1 id="pageTitle">{title}</h1>
    <div class="controls">
      <select id="scenarioSelect" aria-label="Scenario"></select>
      <button id="prevBtn" type="button">&larr; Prev</button>
      <button id="playBtn" type="button">Play</button>
      <button id="nextBtn" type="button">Next &rarr;</button>
      <select id="speedSelect" aria-label="Playback interval">
        <option value="500">2 fps (desktop-safe)</option>
        <option value="250" selected>4 fps</option>
        <option value="120">8 fps</option>
      </select>
    </div>
  </header>

  <main>
    <section class="card">
      <div class="canvas-wrap">
        <canvas id="mazeCanvas" width="720" height="540"></canvas>
      </div>
      <div class="scrubber">
        <span id="stepLabel">Step 0 / 0</span>
        <input id="stepSlider" type="range" min="0" max="0" value="0" />
      </div>
      <div class="legend">
        <div class="legend-item"><span class="swatch" style="background:#f0dfce"></span>0: Path</div>
        <div class="legend-item"><span class="swatch" style="background:#64748b"></span>1: Wall</div>
        <div class="legend-item"><span class="swatch" style="background:#ec4899"></span>A1: Vanguard</div>
        <div class="legend-item"><span class="swatch" style="background:#38bdf8"></span>A2: Scout</div>
        <div class="legend-item"><span class="swatch" style="background:#a855f7"></span>A3: Support</div>
        <div class="legend-item"><span class="swatch" style="background:#22c55e"></span>P/C: Survivor</div>
        <div class="legend-item"><span class="swatch" style="background:#f97316"></span>D: Heavy Door</div>
        <div class="legend-item"><span class="swatch" style="background:#eab308"></span>I: Invite Marker</div>
        <div class="legend-item"><span class="swatch" style="background:#ef4444"></span>O: Dead-End</div>
      </div>
    </section>

    <aside class="card">
      <div class="metrics">
        <div class="metric-box">
          <div class="metric-label">Rescued / Goal</div>
          <div class="metric-val" id="mRescued">-</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Steps Taken</div>
          <div class="metric-val" id="mSteps">-</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Doors Opened</div>
          <div class="metric-val" id="mDoors">-</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Markers ('I'/'O')</div>
          <div class="metric-val" id="mMarkers">-</div>
        </div>
      </div>
      <div>
        <div class="metric-label" style="margin-bottom:6px">Frame Telemetry &amp; Agent States</div>
        <pre id="frameInfo">Loading replay...</pre>
      </div>
    </aside>
  </main>

  <script>
    const DATA = {payload_json};
    const canvas = document.getElementById("mazeCanvas");
    const ctx = canvas.getContext("2d");
    const scenarioSelect = document.getElementById("scenarioSelect");
    const stepSlider = document.getElementById("stepSlider");
    const stepLabel = document.getElementById("stepLabel");
    const playBtn = document.getElementById("playBtn");
    const speedSelect = document.getElementById("speedSelect");

    let scenarioIdx = 0;
    let frameIdx = 0;
    let timer = null;

    const AGENT_COLORS = {{
      "A1": "#ec4899",
      "A2": "#38bdf8",
      "A3": "#a855f7",
      "A":  "#ec4899"
    }};

    function populateScenarios() {{
      scenarioSelect.innerHTML = "";
      DATA.scenarios.forEach((sc, idx) => {{
        const opt = document.createElement("option");
        opt.value = String(idx);
        opt.textContent = sc.name || ("Scenario " + (idx + 1));
        scenarioSelect.appendChild(opt);
      }});
    }}

    function currentScenario() {{
      return DATA.scenarios[scenarioIdx] || {{ frames: [], summary: {{}} }};
    }}

    function drawFrame() {{
      const sc = currentScenario();
      const frames = sc.frames || [];
      if (!frames.length) return;
      frameIdx = Math.max(0, Math.min(frameIdx, frames.length - 1));
      const frame = frames[frameIdx];
      const grid = frame.schema || [];
      const rows = grid.length;
      const cols = rows > 0 ? grid[0].length : 0;

      const cellSize = Math.max(18, Math.min(44, Math.floor(720 / Math.max(cols, 1))));
      canvas.width = Math.max(1, cols * cellSize);
      canvas.height = Math.max(1, rows * cellSize);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (let r = 0; r < rows; r++) {{
        for (let c = 0; c < cols; c++) {{
          const raw = String(grid[r][c]);
          const x = c * cellSize;
          const y = r * cellSize;

          // Base tile
          ctx.fillStyle = raw === "1" ? "#64748b" : (DATA.bg_colour || "#f0dfce");
          ctx.fillRect(x, y, cellSize, cellSize);
          ctx.strokeStyle = DATA.line_colour || "#1f2937";
          ctx.lineWidth = 1;
          ctx.strokeRect(x, y, cellSize, cellSize);

          const head = raw[0];
          if (head === "A") {{
            const pad = cellSize * 0.16;
            ctx.fillStyle = AGENT_COLORS[raw] || AGENT_COLORS["A"];
            ctx.fillRect(x + pad, y + pad, cellSize - 2 * pad, cellSize - 2 * pad);
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold " + Math.max(10, Math.floor(cellSize * 0.36)) + "px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(raw, x + cellSize / 2, y + cellSize / 2);
          }} else if (head === "P" || head === "C") {{
            const pad = cellSize * 0.2;
            ctx.fillStyle = "#22c55e";
            ctx.beginPath();
            ctx.arc(x + cellSize / 2, y + cellSize / 2, (cellSize - 2 * pad) / 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = "#052e16";
            ctx.font = "bold " + Math.max(10, Math.floor(cellSize * 0.34)) + "px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(raw, x + cellSize / 2, y + cellSize / 2);
          }} else if (raw === "D") {{
            const pad = cellSize * 0.12;
            ctx.fillStyle = "#f97316";
            ctx.fillRect(x + pad, y + pad, cellSize - 2 * pad, cellSize - 2 * pad);
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold " + Math.max(10, Math.floor(cellSize * 0.4)) + "px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("D", x + cellSize / 2, y + cellSize / 2);
          }} else if (raw === "I" || raw === "O") {{
            const pad = cellSize * 0.22;
            ctx.fillStyle = raw === "I" ? "#eab308" : "#ef4444";
            ctx.fillRect(x + pad, y + pad, cellSize - 2 * pad, cellSize - 2 * pad);
            ctx.fillStyle = "#0f172a";
            ctx.font = "bold " + Math.max(10, Math.floor(cellSize * 0.36)) + "px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(raw, x + cellSize / 2, y + cellSize / 2);
          }}
        }}
      }}

      stepSlider.max = String(Math.max(0, frames.length - 1));
      stepSlider.value = String(frameIdx);
      stepLabel.textContent = "Step " + (frame.step ?? frameIdx) + " (" + (frameIdx + 1) + " / " + frames.length + ")";

      const sum = sc.summary || {{}};
      document.getElementById("mRescued").textContent =
        (sum.actual_rescued_count ?? "-") + " / " + (sum.targets_goal ?? "-");
      document.getElementById("mSteps").textContent = String(sum.steps_taken ?? frames.length);
      document.getElementById("mDoors").textContent = String((sum.doors_unlocked || []).length);
      document.getElementById("mMarkers").textContent = String(sum.markers_dropped_count ?? 0);

      document.getElementById("frameInfo").textContent = JSON.stringify(
        {{
          scenario: sc.name,
          step: frame.step ?? frameIdx,
          meta: frame.meta || {{}},
          summary: sum
        }},
        null,
        2
      );
    }}

    function stopPlayback() {{
      if (timer !== null) {{
        clearInterval(timer);
        timer = null;
        playBtn.textContent = "Play";
      }}
    }}

    function togglePlayback() {{
      if (timer !== null) {{
        stopPlayback();
        return;
      }}
      playBtn.textContent = "Pause";
      const intervalMs = parseInt(speedSelect.value, 10) || 250;
      timer = setInterval(() => {{
        const frames = currentScenario().frames || [];
        if (frameIdx + 1 >= frames.length) {{
          stopPlayback();
        }} else {{
          frameIdx += 1;
          drawFrame();
        }}
      }}, intervalMs);
    }}

    scenarioSelect.addEventListener("change", () => {{
      stopPlayback();
      scenarioIdx = parseInt(scenarioSelect.value, 10) || 0;
      frameIdx = 0;
      drawFrame();
    }});
    stepSlider.addEventListener("input", () => {{
      stopPlayback();
      frameIdx = parseInt(stepSlider.value, 10) || 0;
      drawFrame();
    }});
    document.getElementById("prevBtn").addEventListener("click", () => {{
      stopPlayback();
      frameIdx = Math.max(0, frameIdx - 1);
      drawFrame();
    }});
    document.getElementById("nextBtn").addEventListener("click", () => {{
      stopPlayback();
      const frames = currentScenario().frames || [];
      frameIdx = Math.min(frames.length - 1, frameIdx + 1);
      drawFrame();
    }});
    playBtn.addEventListener("click", togglePlayback);
    speedSelect.addEventListener("change", () => {{
      if (timer !== null) {{
        stopPlayback();
        togglePlayback();
      }}
    }});

    populateScenarios();
    drawFrame();
  </script>
</body>
</html>
"""


class MazeGrid:
    """
    Browser-based grid & replay viewer (zero native GUI dependencies).

    Preserves the `MazeGrid(schema, rows, columns, bg_colour, line_colour)`
    interface (`update()`, `run()`, `close()`) while rendering via a local
    Python HTTP server + HTML5 Canvas page viewable in Chrome.
    """

    def __init__(
        self,
        schema: Sequence[Sequence[Any]],
        rows: Optional[int] = None,
        columns: Optional[int] = None,
        bg_colour: str = "#f0dfce",
        line_colour: str = "#1f2937",
        title: str = "Resilient SAR — Maze Viewer",
    ) -> None:
        self.schema = _normalize_schema(schema)
        self.rows = rows if rows is not None else len(self.schema)
        self.columns = (
            columns
            if columns is not None
            else (len(self.schema[0]) if self.schema else 0)
        )
        self.bg_colour = bg_colour
        self.line_colour = line_colour
        self.title = title
        self.frames: List[Dict[str, Any]] = [
            {"step": 0, "schema": copy.deepcopy(self.schema), "meta": {}}
        ]
        self._server: Optional[ThreadingHTTPServer] = None

    def update(
        self,
        schema: Sequence[Sequence[Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.schema = _normalize_schema(schema)
        self.frames.append(
            {
                "step": len(self.frames),
                "schema": copy.deepcopy(self.schema),
                "meta": metadata or {},
            }
        )

    def get_scenarios_payload(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": self.title,
                "frames": self.frames,
                "summary": {
                    "rows": self.rows,
                    "columns": self.columns,
                    "steps_taken": max(0, len(self.frames) - 1),
                },
            }
        ]

    def render_html(self) -> str:
        return build_viewer_html(
            scenarios=self.get_scenarios_payload(),
            title=self.title,
            bg_colour=self.bg_colour,
            line_colour=self.line_colour,
        )

    def export_html(self, output_path: str | Path) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render_html(), encoding="utf-8")
        return out

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        serve_replay_app(
            scenarios=self.get_scenarios_payload(),
            host=host,
            port=port,
            title=self.title,
            bg_colour=self.bg_colour,
            line_colour=self.line_colour,
        )

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


def serve_replay_app(
    scenarios: Sequence[Dict[str, Any]],
    host: str = "127.0.0.1",
    port: int = 8000,
    title: str = "Resilient SAR — Local Chrome Replay Workbench",
    bg_colour: str = "#f0dfce",
    line_colour: str = "#1f2937",
) -> None:
    """Starts a local offline HTTP server for Chrome replay inspection."""
    html_bytes = build_viewer_html(
        scenarios=scenarios,
        title=title,
        bg_colour=bg_colour,
        line_colour=line_colour,
    ).encode("utf-8")
    api_bytes = json.dumps({"scenarios": list(scenarios)}).encode("utf-8")

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.end_headers()
                self.wfile.write(html_bytes)
            elif self.path == "/api/replay":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(api_bytes)))
                self.end_headers()
                self.wfile.write(api_bytes)
            elif self.path == "/health":
                body = b'{"status":"ok"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"Resilient SAR Web Viewer running at http://{host}:{port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
