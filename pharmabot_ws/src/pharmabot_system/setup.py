from setuptools import find_packages, setup

package_name = "pharmabot_system"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (
            f"share/{package_name}/launch",
            [
                "launch/pharmabot_demo.launch.py",
                "launch/pharmabot_nav2_integration.launch.py",
                "launch/pharmabot_calibration.launch.py",
                "launch/pharmabot_hospital_world.launch.py",
                "launch/pharmabot_ui.launch.py",
            ],
        ),
        (f"share/{package_name}/config", ["config/pharmacy_service_goals.json"]),
        (f"share/{package_name}/maps", ["maps/pharmacy_map.yaml", "maps/pharmacy_map.pgm"]),
        (f"share/{package_name}/worlds", ["worlds/hospital_pharmacy.sdf"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="PharmaBot Team",
    maintainer_email="student@example.com",
    description="PharmaBot ROS2 project with scheduling, watchdog and dashboard.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "request_generator = pharmabot_system.request_generator_node:main",
            "scheduler = pharmabot_system.scheduler_node:main",
            "task_executor = pharmabot_system.task_executor_node:main",
            "nav_task_executor = pharmabot_system.nav_task_executor_node:main",
            "goal_calibrator = pharmabot_system.goal_calibrator_node:main",
            "ui_server = pharmabot_system.ui_server_node:main",
            "watchdog = pharmabot_system.watchdog_node:main",
            "dashboard = pharmabot_system.dashboard_node:main",
        ],
    },
)
