"""
dashboard_node.py — PharmaBot real-time terminal dashboard.

Renders a colored, live table every 2 s:
  • System status bar  (safe_mode / robot_busy)
  • Full task queue    (priority | service | medication | time left | RT type)
  • Last completed event with deadline result

Color coding:
  CRITICAL  → red        (Hard RT)
  URGENT    → yellow     (Soft RT)
  STANDARD  → cyan       (Firm RT)
  SAFE MODE → red blink  banner
"""
from __future__ import annotations

import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

# ANSI escape codes
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_GRAY   = "\033[90m"
_BG_RED = "\033[41m"

_PRIORITY_COLOR = {
    "CRITICAL": _RED,
    "URGENT":   _YELLOW,
    "STANDARD": _CYAN,
}
_RT_TYPE = {
    "CRITICAL": "Hard RT",
    "URGENT":   "Soft RT",
    "STANDARD": "Firm RT",
}


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bar(seconds_left: int, total: int = 90, width: int = 12) -> str:
    """ASCII progress bar for time remaining."""
    filled = int(width * max(0, seconds_left) / max(1, total))
    bar = "█" * filled + "░" * (width - filled)
    if seconds_left <= 10:
        return _color(bar, _RED)
    if seconds_left <= 30:
        return _color(bar, _YELLOW)
    return _color(bar, _GREEN)


class DashboardNode(Node):
    def __init__(self) -> None:
        super().__init__("dashboard")
        self.safe_mode = False
        self.last_state: dict = {"robot_busy": False, "queue_size": 0, "tasks": []}
        self.last_event: dict | None = None
        self._render_count = 0

        self.sub_state = self.create_subscription(
            String, "/pharmabot/queue_state", self._on_state, 10
        )
        self.sub_safe_mode = self.create_subscription(
            Bool, "/pharmabot/safe_mode", self._on_safe_mode, 10
        )
        self.sub_events = self.create_subscription(
            String, "/pharmabot/deadline_events", self._on_event, 10
        )
        self.timer = self.create_timer(2.0, self._render)
        self.get_logger().info("Dashboard node started — terminal UI active.")

    # ── Subscribers ──────────────────────────────────────────────────────────

    def _on_state(self, msg: String) -> None:
        try:
            self.last_state = json.loads(msg.data)
        except Exception:
            pass

    def _on_safe_mode(self, msg: Bool) -> None:
        self.safe_mode = msg.data

    def _on_event(self, msg: String) -> None:
        try:
            self.last_event = json.loads(msg.data)
        except Exception:
            pass

    # ── Renderer ─────────────────────────────────────────────────────────────

    def _render(self) -> None:
        self._render_count += 1
        robot_busy = self.last_state.get("robot_busy", False)
        queue_size = self.last_state.get("queue_size", 0)
        tasks      = self.last_state.get("tasks", [])

        sep = _color("─" * 68, _GRAY)
        lines: list[str] = ["\n" + sep]

        # ── Header ──
        ts = time.strftime("%H:%M:%S")
        title = _color("  PharmaBot Real-Time Scheduler Dashboard", _BOLD)
        lines.append(f"{title}   {_color(ts, _GRAY)}")
        lines.append(sep)

        # ── Safe mode banner ──
        if self.safe_mode:
            banner = _color(
                "  !! SAFE MODE ACTIVE — Hard RT deadline missed — robot halted !!",
                _BG_RED + _BOLD,
            )
            lines.append(banner)
            lines.append(sep)

        # ── Status line ──
        busy_str = (_color("BUSY  [executing]", _YELLOW) if robot_busy
                    else _color("IDLE  [waiting]",  _GREEN))
        sm_str   = (_color("SAFE MODE ON", _RED) if self.safe_mode
                    else _color("normal", _GREEN))
        lines.append(
            f"  Robot: {busy_str}   Safe mode: {sm_str}   "
            f"Queue: {_color(str(queue_size), _BOLD)} task(s)"
        )
        lines.append(sep)

        # ── Queue table ──
        if not tasks:
            lines.append(_color("  (queue is empty)", _GRAY))
        else:
            header = (
                f"  {'#':<3} {'ID':<10} {'Priority':<10} {'RT Type':<9} "
                f"{'Service':<14} {'Time left':>9}  Bar"
            )
            lines.append(_color(header, _BOLD))
            for idx, t in enumerate(tasks, 1):
                prio    = t.get("priority", "?")
                col     = _PRIORITY_COLOR.get(prio, _RESET)
                rt_type = _RT_TYPE.get(prio, "?")
                svc     = t.get("service", "?")
                t_left  = int(t.get("seconds_left", 0))
                t_max   = {"CRITICAL": 30, "URGENT": 60, "STANDARD": 90}.get(prio, 90)

                row = (
                    f"  {idx:<3} {t.get('task_id', '?'):<10} "
                    f"{_color(f'{prio:<10}', col)}"
                    f"  {_color(rt_type, _GRAY):<8}  "
                    f"{svc:<14} {t_left:>6}s   {_bar(t_left, t_max)}"
                )
                lines.append(row)

        lines.append(sep)

        # ── Last completed event ──
        if self.last_event:
            ev     = self.last_event
            missed = bool(ev.get("deadline_missed"))
            prio   = ev.get("priority", "?")
            result = _color("DEADLINE MISSED", _RED) if missed else _color("On time", _GREEN)
            nav    = ev.get("nav_status", "")
            lines.append(
                f"  Last event: id={ev.get('task_id', '?')} "
                f"priority={_color(prio, _PRIORITY_COLOR.get(prio, _RESET))} "
                f"-> {result}"
                + (f"  [{nav}]" if nav else "")
            )
            lines.append(sep)

        print("\n".join(lines) + "\n", flush=True)
        self.get_logger().info(
            f"[tick#{self._render_count}] busy={robot_busy} "
            f"queue={queue_size} safe_mode={self.safe_mode}"
        )


def main() -> None:
    rclpy.init()
    node = DashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
