"""
scheduler_node.py — PharmaBot priority-based real-time scheduler.

Scheduling policy:
  1. Primary key  : PRIORITY_ORDER  (CRITICAL=0, URGENT=1, STANDARD=2)
  2. Secondary key: deadline_at     (Earliest Deadline First within same priority)

This ensures that among CRITICAL tasks, the one closest to its deadline
is dispatched first (EDF tiebreaking) — a standard RT scheduling approach.

The scheduler also purges expired STANDARD (Firm RT) tasks before dispatching,
since firm deadlines should be cancelled — not executed late.
"""
from __future__ import annotations

import heapq
import json
import time
from typing import List, Tuple

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from .rt_types import MedicationTask, PRIORITY_ORDER, DEADLINES_SEC


class SchedulerNode(Node):
    def __init__(self) -> None:
        super().__init__("rt_scheduler")
        # heap entries: (priority_order, deadline_at, task)
        self.queue: List[Tuple[int, float, MedicationTask]] = []
        self.robot_busy = False
        self._dispatched_count  = 0
        self._purged_count      = 0

        self.sub_requests   = self.create_subscription(
            String, "/pharmabot/requests_in", self._on_request, 10
        )
        self.sub_robot_busy = self.create_subscription(
            Bool, "/pharmabot/robot_busy", self._on_robot_busy, 10
        )
        self.pub_dispatch   = self.create_publisher(String, "/pharmabot/dispatch",     10)
        self.pub_state      = self.create_publisher(String, "/pharmabot/queue_state",  10)
        self.pub_events     = self.create_publisher(String, "/pharmabot/deadline_events", 10)

        self.timer = self.create_timer(1.0, self._tick)
        self.get_logger().info(
            "Real-time scheduler started (Priority + EDF tiebreaking)."
        )

    # ── Subscription callbacks ────────────────────────────────────────────────

    def _on_request(self, msg: String) -> None:
        task = MedicationTask.from_json(msg.data)
        key  = (PRIORITY_ORDER[task.priority], task.deadline_at, task)
        heapq.heappush(self.queue, key)
        self.get_logger().info(
            f"[Scheduler] Queued task {task.task_id} "
            f"({task.priority} / {task.patient_service}) "
            f"deadline in {int(task.deadline_at - time.time())}s"
        )

    def _on_robot_busy(self, msg: Bool) -> None:
        self.robot_busy = msg.data

    # ── Main tick ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = time.time()
        self._purge_expired_standard(now)
        self._publish_queue_state(now)

        if self.robot_busy or not self.queue:
            return

        _, _, task = heapq.heappop(self.queue)
        self._dispatched_count += 1

        out      = String()
        out.data = task.to_json()
        self.pub_dispatch.publish(out)
        self.get_logger().info(
            f"[Scheduler] Dispatched #{self._dispatched_count}: "
            f"task {task.task_id} ({task.priority}) "
            f"-> {task.patient_service}"
        )

    # ── Firm RT purge: cancel STANDARD tasks whose deadline has passed ─────────

    def _purge_expired_standard(self, now: float) -> None:
        new_queue: List[Tuple[int, float, MedicationTask]] = []
        for entry in self.queue:
            _, dl, task = entry
            if task.priority == "STANDARD" and now > dl:
                self._purged_count += 1
                self.get_logger().warning(
                    f"[Scheduler] Firm RT miss: task {task.task_id} "
                    f"(STANDARD) expired before dispatch — cancelled."
                )
                # Publish a cancelled deadline event so Watchdog can track it
                event = {
                    "task_id":        task.task_id,
                    "priority":       task.priority,
                    "deadline_missed": True,
                    "finished_at":     now,
                    "deadline_at":     task.deadline_at,
                    "nav_status":      "CANCELLED_BEFORE_DISPATCH",
                }
                ev_msg      = String()
                ev_msg.data = json.dumps(event)
                self.pub_events.publish(ev_msg)
            else:
                new_queue.append(entry)
        heapq.heapify(new_queue)
        self.queue = new_queue

    # ── Queue state publisher ─────────────────────────────────────────────────

    def _publish_queue_state(self, now: float) -> None:
        serialized = []
        for _, _, task in sorted(self.queue, key=lambda x: (x[0], x[1])):
            serialized.append(
                {
                    "task_id":    task.task_id,
                    "priority":   task.priority,
                    "service":    task.patient_service,
                    "medication": task.medication_name,
                    "seconds_left": max(0, int(task.deadline_at - now)),
                }
            )
        state = {
            "robot_busy":       self.robot_busy,
            "queue_size":       len(self.queue),
            "tasks":            serialized,
            "dispatched_total": self._dispatched_count,
            "purged_total":     self._purged_count,
        }
        msg      = String()
        msg.data = json.dumps(state)
        self.pub_state.publish(msg)


def main() -> None:
    rclpy.init()
    node = SchedulerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
