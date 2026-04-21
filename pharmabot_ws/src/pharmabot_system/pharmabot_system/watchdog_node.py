"""
watchdog_node.py — PharmaBot fault-tolerance watchdog.

Behaviour per RT type:
  CRITICAL (Hard RT)  → activate safe_mode immediately on deadline miss.
                         Auto-recovery after RECOVERY_TIMEOUT_SEC if next
                         task completes on time.
  URGENT   (Soft RT)  → warn only; quality degraded but system continues.
  STANDARD (Firm RT)  → warn that task is cancelled (firm deadline policy).

The node also publishes /pharmabot/watchdog_status (String JSON) every
HEARTBEAT_SEC so the UI can display watchdog health.
"""
from __future__ import annotations

import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

RECOVERY_TIMEOUT_SEC = 30  # seconds before watchdog allows auto-recovery attempt


class WatchdogNode(Node):
    def __init__(self) -> None:
        super().__init__("watchdog_recovery")

        self.in_safe_mode = False
        self._safe_mode_since: float | None = None
        self._missed_critical_count = 0
        self._missed_urgent_count   = 0
        self._missed_standard_count = 0
        self._total_events          = 0
        self._ontime_count          = 0

        self.sub_events = self.create_subscription(
            String, "/pharmabot/deadline_events", self._on_event, 10
        )
        self.pub_safe_mode = self.create_publisher(Bool,   "/pharmabot/safe_mode",      10)
        self.pub_status    = self.create_publisher(String, "/pharmabot/watchdog_status", 10)

        self.heartbeat_timer = self.create_timer(5.0, self._heartbeat)
        self.get_logger().info("Watchdog node started.")

    # ── Event handler ─────────────────────────────────────────────────────────

    def _on_event(self, msg: String) -> None:
        try:
            event = json.loads(msg.data)
        except Exception:
            return

        priority       = event.get("priority", "")
        deadline_missed = bool(event.get("deadline_missed", False))
        task_id        = event.get("task_id", "?")
        self._total_events += 1

        if not deadline_missed:
            # Successful task — potentially recover from safe mode
            self._ontime_count += 1
            if self.in_safe_mode:
                elapsed = time.time() - (self._safe_mode_since or 0.0)
                if elapsed >= RECOVERY_TIMEOUT_SEC:
                    self._set_safe_mode(False)
                    self.get_logger().info(
                        f"[Watchdog] Recovery: task {task_id} completed on time "
                        f"after {elapsed:.0f}s in safe mode. System restored."
                    )
            return

        # ── Deadline missed ────────────────────────────────────────────────
        if priority == "CRITICAL":
            self._missed_critical_count += 1
            self._set_safe_mode(True)
            self.get_logger().error(
                f"[Watchdog] HARD RT FAILURE on task {task_id} (CRITICAL). "
                f"Safe mode activated. Missed so far: {self._missed_critical_count}"
            )

        elif priority == "URGENT":
            self._missed_urgent_count += 1
            self.get_logger().warning(
                f"[Watchdog] Soft RT miss on task {task_id} (URGENT). "
                f"Degraded quality acceptable. Total soft misses: {self._missed_urgent_count}"
            )

        elif priority == "STANDARD":
            self._missed_standard_count += 1
            self.get_logger().warning(
                f"[Watchdog] Firm RT miss on task {task_id} (STANDARD). "
                f"Task cancelled. Total firm misses: {self._missed_standard_count}"
            )

    # ── Safe mode toggle ─────────────────────────────────────────────────────

    def _set_safe_mode(self, enabled: bool) -> None:
        if enabled and not self.in_safe_mode:
            self._safe_mode_since = time.time()
        elif not enabled:
            self._safe_mode_since = None

        self.in_safe_mode = enabled
        out = Bool()
        out.data = enabled
        self.pub_safe_mode.publish(out)

    # ── Heartbeat status ─────────────────────────────────────────────────────

    def _heartbeat(self) -> None:
        status = {
            "timestamp":         time.time(),
            "safe_mode":         self.in_safe_mode,
            "safe_mode_since":   self._safe_mode_since,
            "total_events":      self._total_events,
            "ontime":            self._ontime_count,
            "missed_critical":   self._missed_critical_count,
            "missed_urgent":     self._missed_urgent_count,
            "missed_standard":   self._missed_standard_count,
        }
        out = String()
        out.data = json.dumps(status)
        self.pub_status.publish(out)
        self.get_logger().info(
            f"[Watchdog] heartbeat — safe={self.in_safe_mode} "
            f"events={self._total_events} "
            f"missed(C/U/S)={self._missed_critical_count}/"
            f"{self._missed_urgent_count}/{self._missed_standard_count}"
        )


def main() -> None:
    rclpy.init()
    node = WatchdogNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
