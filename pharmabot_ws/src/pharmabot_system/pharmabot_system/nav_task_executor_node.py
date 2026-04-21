import json
import math
from pathlib import Path
import time
from typing import Dict, Optional

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient, ClientGoalHandle
from rclpy.node import Node
from std_msgs.msg import Bool, String

from .rt_types import MedicationTask


DEFAULT_SERVICE_GOALS = {
    "Reanimation": {"x": 2.0, "y": 2.0, "yaw": 0.0},
    "Emergency": {"x": 1.0, "y": -1.5, "yaw": 1.57},
    "Consultation": {"x": -1.8, "y": 1.2, "yaw": 3.14},
    "Surgery": {"x": -2.2, "y": -1.0, "yaw": -1.57},
}


class NavTaskExecutorNode(Node):
    def __init__(self) -> None:
        super().__init__("nav_task_executor")

        self.declare_parameter("map_frame", "map")
        self.declare_parameter("use_sim_time", True)
        self.declare_parameter("service_goals_json", json.dumps(DEFAULT_SERVICE_GOALS))
        self.declare_parameter("service_goals_file", "")

        self.current_task: Optional[MedicationTask] = None
        self.current_goal_handle: Optional[ClientGoalHandle] = None
        self.standard_deadline_cancelled = False

        self.nav_client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.sub_dispatch = self.create_subscription(
            String, "/pharmabot/dispatch", self._on_dispatch, 10
        )
        self.sub_safe_mode = self.create_subscription(
            Bool, "/pharmabot/safe_mode", self._on_safe_mode, 10
        )
        self.pub_busy = self.create_publisher(Bool, "/pharmabot/robot_busy", 10)
        self.pub_events = self.create_publisher(String, "/pharmabot/deadline_events", 10)
        self.timer = self.create_timer(0.5, self._tick)

        self.service_goals = self._load_service_goals()
        self.map_frame = self.get_parameter("map_frame").get_parameter_value().string_value
        self.get_logger().info("Nav2 task executor started.")
        self.get_logger().info(f"Loaded goals for services: {', '.join(sorted(self.service_goals.keys()))}")

    def _on_dispatch(self, msg: String) -> None:
        if self.current_task is not None:
            self.get_logger().warning("Received dispatch while busy. Ignoring.")
            return

        task = MedicationTask.from_json(msg.data)
        if task.patient_service not in self.service_goals:
            self.get_logger().error(
                f"No navigation goal configured for service '{task.patient_service}'."
            )
            self._publish_event(task, deadline_missed=True, status="NO_GOAL_CONFIG")
            return

        if not self.nav_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("Nav2 action server not available on /navigate_to_pose.")
            self._publish_event(task, deadline_missed=True, status="NAV2_UNAVAILABLE")
            return

        self.current_task = task
        self.standard_deadline_cancelled = False
        self._publish_busy(True)
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._build_pose(task.patient_service)

        send_future = self.nav_client.send_goal_async(goal_msg)
        send_future.add_done_callback(self._on_goal_response)
        self.get_logger().info(
            f"Sent Nav2 goal for task {task.task_id} ({task.priority}) to service {task.patient_service}"
        )

    def _on_goal_response(self, future) -> None:
        if self.current_task is None:
            return
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f"Nav2 rejected goal for task {self.current_task.task_id}")
            task = self.current_task
            self.current_task = None
            self._publish_busy(False)
            self._publish_event(task, deadline_missed=True, status="GOAL_REJECTED")
            return

        self.current_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_goal_result)

    def _on_goal_result(self, future) -> None:
        if self.current_task is None:
            return

        task = self.current_task
        self.current_task = None
        self.current_goal_handle = None
        self._publish_busy(False)

        result = future.result()
        status = result.status
        now = time.time()
        deadline_missed = now > task.deadline_at or self.standard_deadline_cancelled

        if status == GoalStatus.STATUS_SUCCEEDED:
            status_text = "SUCCEEDED"
        elif status == GoalStatus.STATUS_CANCELED:
            status_text = "CANCELED"
        elif status == GoalStatus.STATUS_ABORTED:
            status_text = "ABORTED"
        else:
            status_text = f"STATUS_{status}"

        self._publish_event(task, deadline_missed=deadline_missed, status=status_text)

    def _on_safe_mode(self, msg: Bool) -> None:
        if not msg.data:
            return
        if self.current_goal_handle is None:
            return
        self.get_logger().warning("Safe mode active: canceling current navigation goal.")
        self.current_goal_handle.cancel_goal_async()

    def _tick(self) -> None:
        if self.current_task is None:
            self._publish_busy(False)
            return
        if self.current_goal_handle is None:
            return

        now = time.time()
        if now <= self.current_task.deadline_at:
            return

        if self.current_task.priority == "STANDARD" and not self.standard_deadline_cancelled:
            # Firm deadline policy: cancel if deadline has passed.
            self.standard_deadline_cancelled = True
            self.get_logger().warning(
                f"Firm RT deadline passed for task {self.current_task.task_id}: canceling Nav2 goal."
            )
            self.current_goal_handle.cancel_goal_async()

    def _build_pose(self, service_name: str) -> PoseStamped:
        goal_cfg = self.service_goals[service_name]
        pose = PoseStamped()
        pose.header.frame_id = self.map_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(goal_cfg["x"])
        pose.pose.position.y = float(goal_cfg["y"])
        pose.pose.position.z = 0.0

        yaw = float(goal_cfg.get("yaw", 0.0))
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def _publish_event(self, task: MedicationTask, deadline_missed: bool, status: str) -> None:
        event = {
            "task_id": task.task_id,
            "priority": task.priority,
            "deadline_missed": deadline_missed,
            "finished_at": time.time(),
            "deadline_at": task.deadline_at,
            "nav_status": status,
        }
        out = String()
        out.data = json.dumps(event)
        self.pub_events.publish(out)

    def _publish_busy(self, busy: bool) -> None:
        msg = Bool()
        msg.data = busy
        self.pub_busy.publish(msg)

    def _load_service_goals(self) -> Dict[str, Dict[str, float]]:
        file_path = self.get_parameter("service_goals_file").get_parameter_value().string_value.strip()
        if file_path:
            path = Path(file_path)
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                return loaded
            self.get_logger().warning(
                f"Configured service_goals_file not found: {file_path}. Falling back to service_goals_json."
            )

        goals_json = self.get_parameter("service_goals_json").get_parameter_value().string_value
        return json.loads(goals_json)


def main() -> None:
    rclpy.init()
    node = NavTaskExecutorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
