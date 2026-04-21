# Guide Parfait Ubuntu + ROS2 + PharmaBot

Ce guide est adapte a votre machine: **Ubuntu 24.04 (noble)** avec **ROS2 Jazzy**.
Il inclut aussi un rappel rapide pour Ubuntu 22.04.

## 1) Preparation systeme

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl wget git build-essential python3-pip python3-venv
```

## 2) Installation ROS2 Jazzy (Ubuntu 24.04)

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe -y
sudo apt update

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | \
sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-jazzy-desktop
```

## 3) Outils ROS2 et dependances projet

```bash
sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-vcstool
sudo rosdep init
rosdep update

sudo apt install -y ros-jazzy-navigation2 ros-jazzy-nav2-bringup
sudo apt install -y ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-simulations
sudo apt install -y ros-jazzy-ros-gz ros-jazzy-ros-gz-sim
```

Important (Ubuntu 24.04):
- Ne pas installer `gazebo` classique (souvent indisponible sur noble).
- Ne pas utiliser le wildcard `ros-jazzy-turtlebot3*` (installe trop de paquets inutiles).
- Utiliser les paquets ci-dessus (`turtlebot3`, `turtlebot3-simulations`, `ros-gz`).

## 4) Activer ROS2 automatiquement

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## 5) Cloner et compiler le projet

```bash
cd ~
git clone https://github.com/rachid123RA/rachid-PharmaBot.git
cd rachid-PharmaBot/pharmabot_ws

rosdep install --from-paths src --ignore-src -r -y
colcon build
source install/setup.bash
```

## 6) Lancer PharmaBot (Phase 2)

```bash
export TURTLEBOT3_MODEL=burger
ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py start_sim_stack:=true
```

## 7) Calibration RViz (optionnel)

Dans un nouveau terminal:

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch pharmabot_system pharmabot_calibration.launch.py \
  output_file:=/tmp/pharmacy_service_goals_calibrated.json
```

Puis relancer avec objectifs calibres:

```bash
ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py \
  service_goals_file:=/tmp/pharmacy_service_goals_calibrated.json
```

## 8) Verification rapide

```bash
ros2 --version
echo $ROS_DISTRO
```

Vous devez voir `jazzy`.

## 9) Si vous etes sur Ubuntu 22.04

- Installer `ros-humble-desktop` (pas jazzy)
- Adapter les paquets en `ros-humble-*`
- Sourcer `/opt/ros/humble/setup.bash`
