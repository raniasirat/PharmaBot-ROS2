import random

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .rt_types import MedicationTask


class RequestGeneratorNode(Node):
    def __init__(self) -> None:
        super().__init__("request_generator")
        self.publisher = self.create_publisher(String, "/pharmabot/requests_in", 10)
        self.timer = self.create_timer(2.5, self._publish_request)
        self.get_logger().info("Request generator started.")

    def _publish_request(self) -> None:
        priority = random.choices(
            population=["CRITICAL", "URGENT", "STANDARD"],
            weights=[0.2, 0.35, 0.45],
            k=1,
        )[0]
        service = random.choice(["Reanimation", "Emergency", "Consultation", "Surgery"])
        med = random.choice(["Epinephrine", "Morphine", "Paracetamol", "Antibiotic"])
        exec_time = random.randint(8, 25)

        task = MedicationTask.new_random(priority, service, med, exec_time)
        msg = String()
        msg.data = task.to_json()
        self.publisher.publish(msg)
        self.get_logger().info(
            f"New request: id={task.task_id} priority={task.priority} deadline={int(task.deadline_at)}"
        )


def main() -> None:
    rclpy.init()
    node = RequestGeneratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
