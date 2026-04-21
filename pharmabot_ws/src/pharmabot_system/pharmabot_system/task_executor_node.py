import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from .rt_types import MedicationTask


class TaskExecutorNode(Node):
    def __init__(self) -> None:
        super().__init__("task_executor")
        self.current_task: MedicationTask | None = None
        self.task_end_time = 0.0

        self.sub_dispatch = self.create_subscription(
            String, "/pharmabot/dispatch", self._on_dispatch, 10
        )
        self.pub_busy = self.create_publisher(Bool, "/pharmabot/robot_busy", 10)
        self.pub_events = self.create_publisher(String, "/pharmabot/deadline_events", 10)
        self.timer = self.create_timer(0.5, self._tick)
        self.get_logger().info("Task executor started.")

    def _on_dispatch(self, msg: String) -> None:
        if self.current_task is not None:
            self.get_logger().warning("Received dispatch while busy. Ignoring.")
            return

        self.current_task = MedicationTask.from_json(msg.data)
        self.task_end_time = time.time() + self.current_task.estimated_exec_sec
        self._publish_busy(True)
        self.get_logger().info(
            f"Executing task {self.current_task.task_id} for {self.current_task.estimated_exec_sec}s"
        )

    def _tick(self) -> None:
        if self.current_task is None:
            self._publish_busy(False)
            return

        if time.time() < self.task_end_time:
            return

        now = time.time()
        task = self.current_task
        self.current_task = None
        self._publish_busy(False)

        deadline_missed = now > task.deadline_at
        event = {
            "task_id": task.task_id,
            "priority": task.priority,
            "deadline_missed": deadline_missed,
            "finished_at": now,
            "deadline_at": task.deadline_at,
        }
        out = String()
        out.data = json.dumps(event)
        self.pub_events.publish(out)

        if deadline_missed:
            self.get_logger().warning(
                f"Task {task.task_id} missed deadline ({task.priority})"
            )
        else:
            self.get_logger().info(f"Task {task.task_id} completed on time")

    def _publish_busy(self, busy: bool) -> None:
        msg = Bool()
        msg.data = busy
        self.pub_busy.publish(msg)


def main() -> None:
    rclpy.init()
    node = TaskExecutorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
