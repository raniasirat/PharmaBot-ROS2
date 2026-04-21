# Guide Test Simple (Ubuntu) - PharmaBot

Ce guide est ecrit pour debutant, en mode tres simple.

## 1) C'est quoi cette application ?

PharmaBot simule un robot pharmacie dans ROS2.
Le robot recoit des demandes medicaments, puis il va vers les services de l'hopital.

Regles de priorite:
- `CRITICAL`: tres urgent (hard deadline)
- `URGENT`: urgent (soft deadline)
- `STANDARD`: normal (firm deadline)

## 2) Avant de lancer

Ouvrir un terminal Ubuntu:

```bash
source /opt/ros/jazzy/setup.bash
echo $ROS_DISTRO
```

Tu dois voir `jazzy`.

## 3) Lancer l'application complete

Dans terminal 1:

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py start_sim_stack:=true
```

Attends 20 a 40 secondes (Gazebo + Nav2 + RViz).

## 4) Comment savoir si c'est OK ?

D'apres ta capture RViz, c'est deja bien:
- `Localization: active` = OK
- RViz ouvert avec map = OK
- Le robot peut recevoir des goals Nav2

Pour verifier techniquement, ouvre terminal 2:

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 node list
```

Tu dois voir au moins:
- `/request_generator`
- `/rt_scheduler`
- `/nav_task_executor`
- `/watchdog_recovery`
- `/dashboard`

## 5) Test fonctionnel tres simple (3 minutes)

### Test A - file de taches

Dans terminal 2:

```bash
ros2 topic echo /pharmabot/queue_state
```

Resultat attendu:
- `queue_size` change
- `robot_busy` passe a `true` puis `false`
- des taches apparaissent dans `tasks`

### Test B - events deadlines

Dans terminal 3:

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 topic echo /pharmabot/deadline_events
```

Resultat attendu:
- messages JSON avec `task_id`, `priority`, `deadline_missed`, `nav_status`

### Test C - envoi manuel d'un objectif RViz

Dans RViz:
1. Clique sur outil `Nav2 Goal`
2. Clique un point libre dans la map
3. Le robot doit bouger vers ce point

Si le robot bouge, Nav2 fonctionne.

## 6) Si ca ne marche pas

### Erreur distro

```bash
echo $ROS_DISTRO
```

Si ce n'est pas `jazzy`, refaire:

```bash
source /opt/ros/jazzy/setup.bash
```

### Build propre

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
rm -rf build install log
colcon build
source install/setup.bash
```

### Re-test rapide

```bash
ros2 topic list | rg pharmabot
```

Si les topics `/pharmabot/...` existent, l'app tourne.

### Erreur chemin (la plus frequente)

Si tu vois `No such file or directory`, verifie le dossier:

```bash
cd ~/rachid-PharmaBot/pharmabot_ws
pwd
```

Le resultat doit etre:
`/home/rachid/rachid-PharmaBot/pharmabot_ws`

### Erreur nom launch (faute de frappe)

Commande correcte:

```bash
ros2 launch pharmabot_system pharmabot_nav2_integration.launch.py start_sim_stack:=true
```

Si tu tapes un autre nom, ROS2 va dire que le launch file est introuvable.

### Visualisation ne s'affiche pas dans VMware

1) Activer acceleration 3D dans VMware (VM Settings -> Display -> Accelerate 3D graphics)  
2) Redemarrer Ubuntu  
3) Tester RViz manuellement:

```bash
source /opt/ros/jazzy/setup.bash
rviz2
```

Si `rviz2` s'ouvre, la visualisation marche.
