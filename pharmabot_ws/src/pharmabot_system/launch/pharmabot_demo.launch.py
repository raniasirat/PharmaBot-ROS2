from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="pharmabot_system",
                executable="request_generator",
                output="screen",
            ),
            Node(
                package="pharmabot_system",
                executable="scheduler",
                output="screen",
            ),
            Node(
                package="pharmabot_system",
                executable="task_executor",
                output="screen",
            ),
            Node(
                package="pharmabot_system",
                executable="watchdog",
                output="screen",
            ),
            Node(
                package="pharmabot_system",
                executable="dashboard",
                output="screen",
            ),
        ]
    )
