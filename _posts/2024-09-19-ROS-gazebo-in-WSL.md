---
layout:     post
title:      ROS & gazebo in WSL
subtitle:   
date:       2024-09-19
author:     ��ī�ٳ�
header-img: img/post_ROS.png
catalog: true
tags:
    - ROS
    - gazebo
    - WSL
---

## ǰ��

> ���ļ�¼��wsl��ROS�У���gazeboƽ̨�����˶����档

## �ο�����

- WSL2.2.4.0
- Ubuntu-20.04.6-LTS
- ROS-noetic
- gazebo11

## ������İ�װ

�������������ros��װʱ�Ѿ���װ���ˣ�����������������
```
    ros-noetic-joy ros-noetic-teleop-twist-joy 
    ros-noetic-teleop-twist-keyboard ros-noetic-laser-proc 
    ros-noetic-rgbd-launch ros-noetic-depthimage-to-laserscan 
    ros-noetic-rosserial-arduino ros-noetic-rosserial-python 
    ros-noetic-rosserial-server ros-noetic-rosserial-client 
    ros-noetic-rosserial-msgs ros-noetic-amcl ros-noetic-map-server 
    ros-noetic-move-base ros-noetic-urdf ros-noetic-xacro 
    ros-noetic-compressed-image-transport ros-noetic-rqt* 
    ros-noetic-gmapping ros-noetic-navigation ros-noetic-interactive-markers
```

��������װTurtleBot3�������
```
sudo apt-get install ros-kinetic-dynamixel-sdk
sudo apt-get install ros-kinetic-turtlebot3-msgs
sudo apt-get install ros-kinetic-turtlebot3
```

Ȼ�����ط����
```
cd ~/ros_ws/src/
git clone -b noetic-devel https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
cd ~/ros_ws && catkin_make
```

## �������

������TurtlrBot3��ģ�Ͳ�����
```
export TURTLEBOT3_MODEL=burger
```
��burgle��waffle��waffle_pi����ѡ��<br>
Ȼ������launch�ļ�
```
roslaunch turtlebot3_gazebo turtlebot3_empty_world.launch
```
��򿪲�����һ��С������
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-09-19-ROS&gazebo-in-WSL/1.png)

Ȼ����������insert��������ģ�Ϳ��е�ģ��

![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-09-19-ROS&gazebo-in-WSL/2.png)

���̲���������
```
roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch
```
## ��gmapping���н�ͼ

����ʾ���еĻ�������һ�������״����̼ƣ���˿���ʹ��gmapping����slam��ͼ

������Ҫ����gmapping��Դ��������빤���ռ��srcĿ¼֮��
```
git clone https://github.com/ros-perception/openslam_gmapping.git
git clone https://github.com/ros-perception/slam_gmapping.git
git clone https://github.com/ros-planning/navigation.git
git clone https://github.com/ros/geometry2.git
```
Ȼ�����
```
cd ..
catkin_make
```
��������������Խ����뻺��������±���һ��
```
cd ros_ws/build
rm -rf *
```
����rviz��
```
roslaunch turtlebot3_gazebo turtlebot3_gazebo_rviz.launch
```

![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-09-19-ROS&gazebo-in-WSL/3.png)

����gmapping��:
```
rosrun gmapping slam_gmapping
```
Ȼ���ڴ򿪵�rviz��ͼ�п��Կ�����ͼ�������ƶ������˿��Խ��н�ͼ

![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-09-19-ROS&gazebo-in-WSL/4.png)