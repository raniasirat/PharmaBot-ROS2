# PharmaBot — Workspace README

## Quick start (simulation mode, no ROS2 needed)

```bash
cd pharmabot_ws
colcon build --symlink-install
source install/setup.bash

# Demo only (no Gazebo/Nav2) — scheduler + watchdog + dashboard in terminal
ros2 launch pharmabot_system pharmabot_demo.launch.py
```

## Full simulation (Gazebo + Nav2 + RViz2)

```bash
export TURTLEBOT3_MODEL=burger

# Full stack — Gazebo, Nav2, TurtleBot3, RViz2, PharmaBot nodes
ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py

# Web UI → http://localhost:8080
```

## Launch arguments

| Argument | Default | Description |
|---|---|---|
| `start_sim_stack` | `true` | Launch Gazebo + Nav2 + TurtleBot3 |
| `use_nav2_executor` | `true` | Use real Nav2 navigation (false = simulated timer) |
| `use_sim_time` | `true` | Use Gazebo clock |
| `open_rviz` | `true` | Open RViz2 |
| `service_goals_file` | (auto) | JSON with service→(x,y,yaw) nav goals |

## Node architecture

```
request_generator  →  /pharmabot/requests_in
                              ↓
                       rt_scheduler  (Priority + EDF)
                              ↓ /pharmabot/dispatch
               nav_task_executor  (Nav2 NavigateToPose)
                       ↓ /pharmabot/deadline_events
                   watchdog_recovery
                       ↓ /pharmabot/safe_mode
                   dashboard (terminal)
                   ui_server  → http://localhost:8080
```

## RT deadline policy

| Priority | Deadline | RT Type | Missed deadline |
|---|---|---|---|
| CRITICAL | 30 s | Hard RT | Safe mode + watchdog alert |
| URGENT   | 60 s | Soft RT | Warning only, degraded quality |
| STANDARD | 90 s | Firm RT | Cancelled before or during execution |
