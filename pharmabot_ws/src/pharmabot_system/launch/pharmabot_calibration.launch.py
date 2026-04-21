from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration("use_sim_time")
    output_file = LaunchConfiguration("output_file")

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument(
                "output_file",
                default_value="/tmp/pharmacy_service_goals_calibrated.json",
                description="Where to save captured service goals JSON.",
            ),
            Node(
                package="pharmabot_system",
                executable="goal_calibrator",
                output="screen",
                parameters=[
                    {
                        "use_sim_time": use_sim_time,
                        "output_file": output_file,
                    }
                ],
            ),
        ]
    )
