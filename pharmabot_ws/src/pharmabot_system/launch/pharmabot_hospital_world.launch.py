from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    world = LaunchConfiguration("world")

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"]
            )
        ),
        launch_arguments={
            "gz_args": ["-r ", world],
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("pharmabot_system"),
                        "worlds",
                        "hospital_pharmacy.sdf",
                    ]
                ),
                description="Hospital/pharmacy Gazebo Sim world SDF.",
            ),
            gz,
        ]
    )
