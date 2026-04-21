from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    host = LaunchConfiguration("host")
    port = LaunchConfiguration("port")
    use_sim_time = LaunchConfiguration("use_sim_time")

    return LaunchDescription(
        [
            DeclareLaunchArgument("host", default_value="0.0.0.0"),
            DeclareLaunchArgument("port", default_value="8080"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            Node(
                package="pharmabot_system",
                executable="ui_server",
                output="screen",
                parameters=[
                    {
                        "host": host,
                        "port": port,
                        "use_sim_time": use_sim_time,
                        # If you want a return-to-pharmacy step, add this service to your goal mapping JSON.
                        "pharmacy_service_name": "Pharmacy",
                    }
                ],
            ),
        ]
    )

