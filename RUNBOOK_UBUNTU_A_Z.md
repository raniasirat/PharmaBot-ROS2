# Runbook A → Z (Ubuntu) — PharmaBot

Ce fichier explique **tout**: de `git clone` jusqu’a la visualisation 3D + UI.
Il est adapte a **Ubuntu 24.04 (noble) + ROS2 Jazzy**.

## A) Installer ROS2 + dependances (une seule fois)

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl wget git build-essential python3-pip python3-venv

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

sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-vcstool
sudo rosdep init
rosdep update

sudo apt install -y ros-jazzy-navigation2 ros-jazzy-nav2-bringup
sudo apt install -y ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-simulations
sudo apt install -y ros-jazzy-ros-gz ros-jazzy-ros-gz-sim
```

Activer ROS2 automatiquement:

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
echo $ROS_DISTRO
```

Tu dois voir: `jazzy`.

## B) Cloner le projet (une seule fois)

```bash
cd ~
git clone https://github.com/rachid123RA/rachid-PharmaBot.git
```

## C) Compiler le workspace

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build
source install/setup.bash
```

## D) Run 1 (simple, sans Nav2)

Si tu veux juste voir que l’app tourne (console):

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch pharmabot_system pharmabot_demo.launch.py
```

## E) Run 2 (navigation + RViz + simulation)

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py start_sim_stack:=true
```

Attends 30–60 secondes. Tu dois voir RViz (et la simulation).

### Envoyer un objectif (test rapide)

Dans RViz:
- outil **Nav2 Goal**
- clique sur la map
- le robot doit bouger

## F) UI (interface simple “clic → tache”)

Dans un nouveau terminal:

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch pharmabot_system pharmabot_ui.launch.py
```

Ouvrir dans le navigateur Ubuntu:
- `http://localhost:8080`

Tu peux envoyer une mission:
- medicament X → salle Y → retour Pharmacy

## G) Monde 3D hopital + ground (ros_gz)

Tu peux lancer le monde 3D seul:

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch pharmabot_system pharmabot_hospital_world.launch.py
```

## H) Calibration des positions des salles (optionnel)

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch pharmabot_system pharmabot_calibration.launch.py output_file:=/tmp/pharmacy_service_goals_calibrated.json
```

Puis relancer Nav2 avec le fichier:

```bash
ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py \
  service_goals_file:=/tmp/pharmacy_service_goals_calibrated.json
```

## I) Verifier que tout tourne (debug simple)

```bash
ros2 node list
ros2 topic list | rg pharmabot
ros2 topic echo /pharmabot/queue_state
```

## J) Si tu ne vois pas la visualisation (VMware)

1) VMware → Settings → Display → **Accelerate 3D graphics** = ON  
2) Redemarrer Ubuntu  
3) Tester RViz:

```bash
source /opt/ros/jazzy/setup.bash
rviz2
```

