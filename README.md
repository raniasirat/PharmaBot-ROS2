# rachid-PharmaBot

Autonomous Pharmacy Robot project using ROS2, TurtleBot3, Gazebo, and Nav2.

## Repository content

- `pharmabot_ws/`: ROS2 workspace
- `pharmabot_ws/src/pharmabot_system/`: real-time scheduling prototype
- `Project_Proposal_PharmaBot (1).pdf`: project proposal
- `Guide_Linux_ROS.docx`: Linux/ROS guide

## Quick start (Ubuntu 24.04 + ROS2 Jazzy)

```bash
cd pharmabot_ws
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch pharmabot_system pharmabot_demo.launch.py
```

## Full installation guide

- See `GUIDE_INSTALL_ROS2_UBUNTU.md` for complete setup and run steps.
- See `GUIDE_TEST_SIMPLE_APP.md` for beginner-friendly testing steps.
- See `RUNBOOK_UBUNTU_A_Z.md` for the complete A→Z runbook (clone → build → run → 3D/UI).
