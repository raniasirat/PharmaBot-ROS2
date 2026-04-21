"""
pharmabot_nav2_integration.launch.py
=====================================
Launches the complete PharmaBot stack:

  1. Gazebo Sim  — loads worlds/hospital_pharmacy.sdf
  2. TurtleBot3 Burger  — spawned at pharmacy center (0, 0)
  3. ros_gz_bridge  — /clock, /scan, /odom, /cmd_vel, /tf
  4. robot_state_publisher — URDF joint transforms
  5. Nav2 (map_server + amcl + planner + controller + bt_navigator + lifecycle_manager)
  6. RViz2  — pharmabot_nav2.rviz config (auto-generated if missing)
  7. PharmaBot nodes:
       request_generator | scheduler | nav_task_executor (or task_executor)
       watchdog | dashboard

Usage:
  # Full stack (Gazebo + Nav2 + PharmaBot):
  ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py

  # Without Gazebo (Nav2 + PharmaBot only, Gazebo already running):
  ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py start_sim_stack:=false

  # Simulation mode (no Nav2, just ROS2 scheduler logic):
  ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py use_nav2_executor:=false

  # Custom calibrated goals file:
  ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py \\
      service_goals_file:=/tmp/my_goals.json
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    # ── Launch arguments ─────────────────────────────────────────────────────
    pkg_share = get_package_share_directory("pharmabot_system")

    start_sim_stack  = LaunchConfiguration("start_sim_stack")
    use_nav2_executor = LaunchConfiguration("use_nav2_executor")
    use_sim_time     = LaunchConfiguration("use_sim_time")
    service_goals_file = LaunchConfiguration("service_goals_file")
    open_rviz        = LaunchConfiguration("open_rviz")

    world_file  = os.path.join(pkg_share, "worlds", "hospital_pharmacy.sdf")
    map_yaml    = os.path.join(pkg_share, "maps",   "pharmacy_map.yaml")
    goals_json  = os.path.join(pkg_share, "config", "pharmacy_service_goals.json")

    # TurtleBot3 model
    tb3_model = os.environ.get("TURTLEBOT3_MODEL", "burger")

    # ── Gazebo Sim ────────────────────────────────────────────────────────────
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"]
            )
        ),
        condition=IfCondition(start_sim_stack),
        launch_arguments={
            "gz_args": f"-r {world_file}",
            "on_exit_shutdown": "true",
        }.items(),
    )

    # ── Spawn TurtleBot3 Burger at Pharmacy (0, 0) ────────────────────────────
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",  "turtlebot3_burger",
            "-topic", "robot_description",
            "-x", "0.0", "-y", "0.0", "-z", "0.05",
            "-Y", "0.0",
        ],
        condition=IfCondition(start_sim_stack),
        output="screen",
    )

    # ── Robot State Publisher ─────────────────────────────────────────────────
    # Reads URDF from turtlebot3_description package
    try:
        tb3_desc_pkg = get_package_share_directory("turtlebot3_description")
        urdf_file = os.path.join(tb3_desc_pkg, "urdf", f"turtlebot3_{tb3_model}.urdf")
        with open(urdf_file, "r") as f:
            robot_desc = f.read()
    except Exception:
        robot_desc = ""  # fallback — RSP will warn but not crash

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "robot_description": robot_desc,
        }],
        condition=IfCondition(start_sim_stack),
    )

    # ── ROS-GZ Bridge ─────────────────────────────────────────────────────────
    # Bridges Gazebo topics to ROS2 topics needed by Nav2 and the robot
    gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_bridge",
        output="screen",
        condition=IfCondition(start_sim_stack),
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ── Nav2 stack ────────────────────────────────────────────────────────────
    # We use nav2_bringup's navigation_launch.py for the full stack.
    # The map is served by map_server (static map from our PGM).
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")

    nav2_stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, "launch", "navigation_launch.py")
        ),
        condition=IfCondition(start_sim_stack),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "map": map_yaml,
            "params_file": os.path.join(nav2_bringup_dir, "params", "nav2_params.yaml"),
        }.items(),
    )

    # Map server (standalone — used when start_sim_stack=false but nav2 already up)
    map_server_standalone = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        condition=UnlessCondition(start_sim_stack),
        parameters=[{
            "use_sim_time": use_sim_time,
            "yaml_filename": map_yaml,
        }],
    )

    # ── RViz2 ─────────────────────────────────────────────────────────────────
    # Default RViz2 config from nav2_bringup — shows robot, map, path, laser
    rviz_cfg = os.path.join(nav2_bringup_dir, "rviz", "nav2_default_view.rviz")

    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_cfg],
        condition=IfCondition(open_rviz),
        parameters=[{"use_sim_time": use_sim_time}],
        output="screen",
    )

    # ── PharmaBot nodes ───────────────────────────────────────────────────────
    request_generator = Node(
        package="pharmabot_system",
        executable="request_generator",
        name="request_generator",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    scheduler = Node(
        package="pharmabot_system",
        executable="scheduler",
        name="rt_scheduler",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    nav_task_executor = Node(
        package="pharmabot_system",
        executable="nav_task_executor",
        name="nav_task_executor",
        output="screen",
        condition=IfCondition(use_nav2_executor),
        parameters=[{
            "use_sim_time": use_sim_time,
            "service_goals_file": service_goals_file,
        }],
    )

    task_executor_sim = Node(
        package="pharmabot_system",
        executable="task_executor",
        name="task_executor",
        output="screen",
        condition=UnlessCondition(use_nav2_executor),
        parameters=[{"use_sim_time": use_sim_time}],
    )

    watchdog = Node(
        package="pharmabot_system",
        executable="watchdog",
        name="watchdog_recovery",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    dashboard = Node(
        package="pharmabot_system",
        executable="dashboard",
        name="dashboard",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    ui_server = Node(
        package="pharmabot_system",
        executable="ui_server",
        name="pharmabot_ui",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "host": "0.0.0.0",
            "port": 8080,
        }],
    )

    # ── Log summary ───────────────────────────────────────────────────────────
    log_info = LogInfo(msg=[
        "\n",
        "=" * 60, "\n",
        "  PharmaBot Hospital Navigation Stack\n",
        "  World:  hospital_pharmacy.sdf\n",
        f"  Map:    {map_yaml}\n",
        f"  Goals:  {goals_json}\n",
        "  UI:     http://localhost:8080\n",
        "=" * 60,
    ])

    return LaunchDescription([
        # ── Arguments ──
        DeclareLaunchArgument(
            "start_sim_stack", default_value="true",
            description="Launch Gazebo + Nav2 + TurtleBot3 simulation."),
        DeclareLaunchArgument(
            "use_nav2_executor", default_value="true",
            description="Use Nav2 NavigateToPose executor (vs simulated timer executor)."),
        DeclareLaunchArgument(
            "use_sim_time", default_value="true",
            description="Use Gazebo simulation time."),
        DeclareLaunchArgument(
            "service_goals_file", default_value=goals_json,
            description="JSON file with service→(x,y,yaw) nav goals."),
        DeclareLaunchArgument(
            "open_rviz", default_value="true",
            description="Open RViz2 for visualisation."),

        # ── Sim stack (delayed slightly so Gazebo loads first) ──
        log_info,
        gz_sim,
        robot_state_publisher,
        gz_bridge,

        # Spawn robot after 3 s so Gazebo has time to load the world
        TimerAction(period=3.0, actions=[spawn_robot]),

        # Start Nav2 after 5 s (needs Gazebo + robot running)
        TimerAction(period=5.0, actions=[nav2_stack]),

        # RViz2 after 6 s
        TimerAction(period=6.0, actions=[rviz2]),

        # Map server standalone mode
        map_server_standalone,

        # PharmaBot logic nodes — start after 8 s to let Nav2 fully initialize
        TimerAction(period=8.0, actions=[
            request_generator,
            scheduler,
            nav_task_executor,
            task_executor_sim,
            watchdog,
            dashboard,
            ui_server,
        ]),
    ])
