"""
ui_server_node.py — PharmaBot web dashboard (http://localhost:8080).

Exposes:
  GET  /          → HTML UI
  GET  /state     → JSON system state
  POST /submit    → Enqueue a new medication task
  GET  /watchdog  → JSON watchdog statistics
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from .rt_types import MedicationTask

INDEX_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>PharmaBot Dashboard</title>
    <style>
      * { box-sizing: border-box; }
      body { font-family: system-ui, sans-serif; margin: 0; background: #0f1117; color: #e2e8f0; }
      header { background: #1a1f2e; padding: 14px 24px; border-bottom: 1px solid #2d3748;
               display:flex; align-items:center; gap:12px; }
      header h1 { margin:0; font-size:18px; color:#63b3ed; }
      .badge { padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600; }
      .safe  { background:#e53e3e; color:#fff; }
      .ok    { background:#2f855a; color:#fff; }
      main { padding: 20px 24px; }
      .grid { display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:20px; }
      .card { background:#1a1f2e; border:1px solid #2d3748; border-radius:10px; padding:16px; }
      .card h3 { margin:0 0 12px; font-size:14px; color:#a0aec0; text-transform:uppercase; letter-spacing:.05em; }
      label { display:block; font-size:12px; color:#a0aec0; margin-bottom:4px; margin-top:10px; }
      select, input { width:100%; padding:8px 10px; border-radius:6px; border:1px solid #2d3748;
                      background:#0f1117; color:#e2e8f0; font-size:14px; }
      button { width:100%; margin-top:14px; padding:10px; border-radius:8px; border:none;
               background:#3182ce; color:#fff; font-size:14px; font-weight:600; cursor:pointer; }
      button:hover { background:#2b6cb0; }
      table { width:100%; border-collapse:collapse; font-size:13px; }
      th { text-align:left; padding:6px 8px; color:#718096; font-weight:500; border-bottom:1px solid #2d3748; }
      td { padding:6px 8px; border-bottom:1px solid #1a2035; }
      .CRITICAL { color:#fc8181; font-weight:700; }
      .URGENT   { color:#f6ad55; font-weight:600; }
      .STANDARD { color:#63b3ed; }
      .miss { color:#fc8181; } .ok2 { color:#68d391; }
      .bar-wrap { background:#1a2035; border-radius:4px; height:8px; overflow:hidden; }
      .bar-fill  { height:8px; border-radius:4px; transition: width .5s; }
      .stat { font-size:24px; font-weight:700; color:#63b3ed; }
      .stat-label { font-size:12px; color:#718096; }
      .stats-row { display:flex; gap:20px; flex-wrap:wrap; }
      .stat-box { flex:1; min-width:100px; }
      #toast { position:fixed; bottom:20px; right:20px; padding:10px 16px; background:#2f855a;
               color:#fff; border-radius:8px; display:none; font-size:14px; }
    </style>
  </head>
  <body>
    <header>
      <h1>&#x1F916; PharmaBot Dashboard</h1>
      <span id="safe-badge" class="badge ok">Normal</span>
      <span style="margin-left:auto; font-size:12px; color:#718096" id="ts">--</span>
    </header>
    <main>
      <div class="grid">
        <!-- Stats card -->
        <div class="card">
          <h3>System Status</h3>
          <div class="stats-row">
            <div class="stat-box"><div class="stat" id="stat-queue">0</div><div class="stat-label">Queue size</div></div>
            <div class="stat-box"><div class="stat" id="stat-disp">0</div><div class="stat-label">Dispatched</div></div>
            <div class="stat-box"><div class="stat" id="stat-miss">0</div><div class="stat-label">Missed (C/U/S)</div></div>
            <div class="stat-box"><div class="stat" id="stat-purge">0</div><div class="stat-label">Purged (Firm)</div></div>
          </div>
          <div style="margin-top:14px; font-size:13px; color:#a0aec0">
            Robot: <span id="busy-str">--</span>
          </div>
        </div>

        <!-- Submit card -->
        <div class="card">
          <h3>New Mission</h3>
          <label>Priority</label>
          <select id="priority">
            <option>CRITICAL</option>
            <option selected>URGENT</option>
            <option>STANDARD</option>
          </select>
          <label>Service</label>
          <select id="service">
            <option>Reanimation</option>
            <option>Emergency</option>
            <option selected>Consultation</option>
            <option>Surgery</option>
          </select>
          <label>Medication</label>
          <input id="med" value="Paracetamol"/>
          <label>Return to pharmacy?</label>
          <select id="return">
            <option value="yes" selected>Yes</option>
            <option value="no">No</option>
          </select>
          <button onclick="submitTask()">Send Task</button>
        </div>
      </div>

      <!-- Queue table -->
      <div class="card">
        <h3>Task Queue</h3>
        <table>
          <thead><tr>
            <th>#</th><th>ID</th><th>Priority</th><th>RT Type</th>
            <th>Service</th><th>Medication</th><th>Time Left</th><th>Deadline bar</th>
          </tr></thead>
          <tbody id="queue-body"><tr><td colspan="8" style="color:#718096">Empty</td></tr></tbody>
        </table>
      </div>

      <!-- Last event -->
      <div class="card" style="margin-top:16px">
        <h3>Last Completed Task</h3>
        <pre id="last-event" style="margin:0; font-size:12px; color:#a0aec0">—</pre>
      </div>
    </main>

    <div id="toast"></div>

    <script>
      const RT = { CRITICAL:'Hard RT', URGENT:'Soft RT', STANDARD:'Firm RT' };
      const DEADLINE = { CRITICAL:30, URGENT:60, STANDARD:90 };
      const BAR_COLOR = { CRITICAL:'#fc8181', URGENT:'#f6ad55', STANDARD:'#63b3ed' };

      function toast(msg, color='#2f855a') {
        const t = document.getElementById('toast');
        t.textContent = msg; t.style.background = color;
        t.style.display = 'block';
        setTimeout(() => t.style.display = 'none', 2500);
      }

      async function refresh() {
        const [sr, wr] = await Promise.all([fetch('/state'), fetch('/watchdog')]);
        const s = await sr.json();
        const w = await wr.json();

        // Header badge
        const badge = document.getElementById('safe-badge');
        if (s.safe_mode) { badge.textContent='SAFE MODE'; badge.className='badge safe'; }
        else             { badge.textContent='Normal';    badge.className='badge ok';   }

        document.getElementById('ts').textContent = new Date().toLocaleTimeString();
        document.getElementById('busy-str').textContent =
          s.robot_busy ? '🟡 BUSY — executing task' : '🟢 IDLE — waiting for tasks';

        // Stats
        document.getElementById('stat-queue').textContent  = s.queue_size;
        document.getElementById('stat-disp').textContent   = s.dispatched_total ?? '—';
        document.getElementById('stat-miss').textContent   =
          (w.missed_critical ?? 0) + '/' + (w.missed_urgent ?? 0) + '/' + (w.missed_standard ?? 0);
        document.getElementById('stat-purge').textContent  = s.purged_total ?? '—';

        // Queue table
        const tbody = document.getElementById('queue-body');
        if (!s.tasks || s.tasks.length === 0) {
          tbody.innerHTML = '<tr><td colspan="8" style="color:#718096">Empty</td></tr>';
        } else {
          tbody.innerHTML = s.tasks.map((t, i) => {
            const pct = Math.min(100, Math.round(100 * t.seconds_left / (DEADLINE[t.priority] || 90)));
            const barColor = pct < 20 ? '#fc8181' : pct < 50 ? '#f6ad55' : BAR_COLOR[t.priority];
            return `<tr>
              <td>${i+1}</td>
              <td style="font-family:monospace">${t.task_id}</td>
              <td class="${t.priority}">${t.priority}</td>
              <td style="color:#a0aec0">${RT[t.priority]||'?'}</td>
              <td>${t.service}</td>
              <td>${t.medication || '—'}</td>
              <td>${t.seconds_left}s</td>
              <td style="min-width:100px">
                <div class="bar-wrap"><div class="bar-fill" style="width:${pct}%;background:${barColor}"></div></div>
              </td>
            </tr>`;
          }).join('');
        }

        // Last event
        if (s.last_event) {
          const ev = s.last_event;
          const cls = ev.deadline_missed ? 'miss' : 'ok2';
          const result = ev.deadline_missed ? 'DEADLINE MISSED' : 'On time';
          document.getElementById('last-event').innerHTML =
            `<span class="${cls}">&#x25CF; ${result}</span>  ` +
            `id=<b>${ev.task_id}</b>  priority=<span class="${ev.priority}">${ev.priority}</span>` +
            (ev.nav_status ? `  nav=${ev.nav_status}` : '');
        }
      }

      async function submitTask() {
        const priority = document.getElementById('priority').value;
        const service  = document.getElementById('service').value;
        const med      = document.getElementById('med').value;
        const ret      = document.getElementById('return').value;
        const params   = new URLSearchParams({priority, service, med, ret});
        const r        = await fetch('/submit?' + params.toString(), {method:'POST'});
        const j        = await r.json();
        toast(j.ok ? 'Task sent: ' + priority + ' / ' + service : 'Error', j.ok ? '#2f855a' : '#e53e3e');
        await refresh();
      }

      refresh();
      setInterval(refresh, 1500);
    </script>
  </body>
</html>
"""


class _HttpHandler(BaseHTTPRequestHandler):
    server_version = "PharmaBotUI/0.2"

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", INDEX_HTML.encode())
        elif path == "/state":
            self._send(200, "application/json",
                       json.dumps(self.server.node.get_state()).encode())  # type: ignore[attr-defined]
        elif path == "/watchdog":
            self._send(200, "application/json",
                       json.dumps(self.server.node.get_watchdog_stats()).encode())  # type: ignore[attr-defined]
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self) -> None:
        if self.path.startswith("/submit"):
            parsed = urllib.parse.urlparse(self.path)
            qs     = urllib.parse.parse_qs(parsed.query)
            priority = (qs.get("priority", ["URGENT"])[0]).upper()
            service  = qs.get("service",  ["Consultation"])[0]
            med      = qs.get("med",      ["Paracetamol"])[0]
            ret      = (qs.get("ret",     ["yes"])[0]).lower()
            self.server.node.submit_task(  # type: ignore[attr-defined]
                priority, service, med, return_to_pharmacy=(ret == "yes")
            )
            self._send(200, "application/json", b'{"ok": true}')
        else:
            self._send(404, "text/plain", b"not found")

    def log_message(self, fmt: str, *args: Any) -> None:
        return  # silence HTTP logs

    def _send(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class UiServerNode(Node):
    def __init__(self) -> None:
        super().__init__("pharmabot_ui")
        self.declare_parameter("host", "0.0.0.0")
        self.declare_parameter("port", 8080)
        self.declare_parameter("pharmacy_service_name", "Pharmacy")

        self.pub_requests = self.create_publisher(String, "/pharmabot/requests_in", 10)
        self.sub_queue    = self.create_subscription(String, "/pharmabot/queue_state",      self._on_queue,   10)
        self.sub_events   = self.create_subscription(String, "/pharmabot/deadline_events",  self._on_event,   10)
        self.sub_safe     = self.create_subscription(Bool,   "/pharmabot/safe_mode",        self._on_safe,    10)
        self.sub_busy     = self.create_subscription(Bool,   "/pharmabot/robot_busy",       self._on_busy,    10)
        self.sub_watchdog = self.create_subscription(String, "/pharmabot/watchdog_status",  self._on_watchdog, 10)

        self._last_queue_state: Dict[str, Any] = {"queue_size": 0, "robot_busy": False, "tasks": [],
                                                   "dispatched_total": 0, "purged_total": 0}
        self._last_event:   Optional[Dict[str, Any]] = None
        self._watchdog_stats: Dict[str, Any]         = {}
        self._safe_mode  = False
        self._robot_busy = False

        host = self.get_parameter("host").get_parameter_value().string_value
        port = int(self.get_parameter("port").get_parameter_value().integer_value)
        self._start_http(host, port)
        self.get_logger().info(f"UI server ready → http://{host}:{port}")

    def _start_http(self, host: str, port: int) -> None:
        httpd: ThreadingHTTPServer = ThreadingHTTPServer((host, port), _HttpHandler)
        httpd.node = self  # type: ignore[attr-defined]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def _on_queue(self,    msg: String) -> None:
        try: self._last_queue_state = json.loads(msg.data)
        except Exception: pass

    def _on_event(self,   msg: String) -> None:
        try: self._last_event = json.loads(msg.data)
        except Exception: pass

    def _on_safe(self,    msg: Bool)   -> None: self._safe_mode  = bool(msg.data)
    def _on_busy(self,    msg: Bool)   -> None: self._robot_busy = bool(msg.data)

    def _on_watchdog(self, msg: String) -> None:
        try: self._watchdog_stats = json.loads(msg.data)
        except Exception: pass

    def submit_task(self, priority: str, service: str,
                    medication: str, return_to_pharmacy: bool) -> None:
        task = MedicationTask.new_random(priority, service, medication, 15)
        out  = String(); out.data = task.to_json()
        self.pub_requests.publish(out)
        if return_to_pharmacy:
            time.sleep(0.01)
            pharmacy_name = self.get_parameter("pharmacy_service_name").get_parameter_value().string_value
            ret_task = MedicationTask.new_random("STANDARD", pharmacy_name, f"Return({medication})", 10)
            out2     = String(); out2.data = ret_task.to_json()
            self.pub_requests.publish(out2)

    def get_state(self) -> Dict[str, Any]:
        return {
            "safe_mode":        self._safe_mode,
            "robot_busy":       self._robot_busy,
            "queue_size":       int(self._last_queue_state.get("queue_size", 0)),
            "tasks":            self._last_queue_state.get("tasks", []),
            "last_event":       self._last_event,
            "dispatched_total": self._last_queue_state.get("dispatched_total", 0),
            "purged_total":     self._last_queue_state.get("purged_total", 0),
        }

    def get_watchdog_stats(self) -> Dict[str, Any]:
        return self._watchdog_stats


def main() -> None:
    rclpy.init()
    node = UiServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
