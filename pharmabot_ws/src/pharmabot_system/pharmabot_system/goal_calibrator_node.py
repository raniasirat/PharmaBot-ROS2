import json
import math
import os
from typing import Dict, List

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node


class GoalCalibratorNode(Node):
    def __init__(self) -> None:
        super().__init__("goal_calibrator")
        self.declare_parameter(
            "services",
            ["Reanimation", "Emergency", "Consultation", "Surgery"],
        )
        self.declare_parameter(
            "output_file",
            os.path.expanduser("~/pharmacy_service_goals_calibrated.json"),
        )

        self.service_names: List[str] = [
            str(s) for s in self.get_parameter("services").get_parameter_value().string_array_value
        ]
        self.output_file = self.get_parameter("output_file").get_parameter_value().string_value
        self.index = 0
        self.goals: Dict[str, Dict[str, float]] = {}

        self.sub_goal = self.create_subscription(
            PoseStamped, "/goal_pose", self._on_goal_pose, 10
        )

        self.get_logger().info("Goal calibrator started.")
        self.get_logger().info("In RViz use 'Nav2 Goal' tool and click one service at a time.")
        self._log_current_service()

    def _on_goal_pose(self, msg: PoseStamped) -> None:
        if self.index >= len(self.service_names):
            return

        service_name = self.service_names[self.index]
        yaw = self._yaw_from_quaternion(msg.pose.orientation.z, msg.pose.orientation.w)
        self.goals[service_name] = {
            "x": round(float(msg.pose.position.x), 3),
            "y": round(float(msg.pose.position.y), 3),
            "yaw": round(yaw, 3),
        }

        self.get_logger().info(
            f"Captured {service_name}: x={self.goals[service_name]['x']} "
            f"y={self.goals[service_name]['y']} yaw={self.goals[service_name]['yaw']}"
        )

        self.index += 1
        self._write_output_file()

        if self.index >= len(self.service_names):
            self.get_logger().info(
                f"Calibration complete. JSON saved to: {self.output_file}"
            )
            return

        self._log_current_service()

    def _log_current_service(self) -> None:
        self.get_logger().info(
            f"Next click target: {self.service_names[self.index]} ({self.index + 1}/{len(self.service_names)})"
        )

    def _write_output_file(self) -> None:
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.goals, f, indent=2)

    @staticmethod
    def _yaw_from_quaternion(z: float, w: float) -> float:
        # For planar Nav2 goals, x=y=0 and yaw can be recovered from z,w.
        return 2.0 * math.atan2(z, w)


def main() -> None:
    rclpy.init()
    node = GoalCalibratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
