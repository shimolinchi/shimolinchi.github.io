---
layout:     post
title:      ROS & gazebo in WSL
subtitle:   
date:       2024-09-19
author:     试墨临池
header-img: img/post_ROS.png
catalog: true
tags:
    - ROS
    - gazebo
    - WSL
---

## 前言

> 本文记录在wsl的ROS中，用gazebo平台进行运动仿真。

## 参考环境

- WSL2.2.4.0
- Ubuntu-20.04.6-LTS
- ROS-noetic
- gazebo11

## 软件包的安装

依赖的软件包在ros安装时已经安装过了，包含下面的软件包：
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

接下来安装TurtleBot3的软件包
```
sudo apt-get install ros-kinetic-dynamixel-sdk
sudo apt-get install ros-kinetic-turtlebot3-msgs
sudo apt-get install ros-kinetic-turtlebot3
```

然后下载仿真包
```
cd ~/ros_ws/src/
git clone -b noetic-devel https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
cd ~/ros_ws && catkin_make
```

## 进入仿真

先设置TurtlrBot3的模型参数：
```
export TURTLEBOT3_MODEL=burger
```
有burgle、waffle、waffle_pi三种选项<br>
然后启动launch文件
```
roslaunch turtlebot3_gazebo turtlebot3_empty_world.launch
```
会打开并出现一个小机器人
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-09-19-ROS&gazebo-in-WSL/1.png)
然后可以在左边insert插入其他模型库中的模型

键盘操作机器人
```
roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch
```
## 用gmapping进行建图

由于示例中的机器人有一个激光雷达和里程计，因此可以使用gmapping进行slam建图

首先需要下载gmapping的源码包，进入工作空间的src目录之后：
```
git clone https://github.com/ros-perception/openslam_gmapping.git
git clone https://github.com/ros-perception/slam_gmapping.git
git clone https://github.com/ros-planning/navigation.git
git clone https://github.com/ros/geometry2.git
```
然后编译
```
cd ..
catkin_make
```
如果编译出问题可以将编译缓存清除重新编译一次
```
cd ros_ws/build
rm -rf *
```
开启rviz：
```
roslaunch turtlebot3_gazebo turtlebot3_gazebo_rviz.launch
```
运行gmapping包：
```
rosrun gmapping slam_gmapping
```
然后在打开的rviz视图中可以看到地图，键盘移动机器人可以进行建图