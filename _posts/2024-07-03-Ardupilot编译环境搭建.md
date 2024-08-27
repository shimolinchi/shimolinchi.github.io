---
layout:     post
title:      Ardupilot编译环境搭建
subtitle:   总结了Ardupilot开发环境的搭建过程
date:       2024-07-03
author:     试墨临池
header-img: img/post_Ardupilot.jpg
catalog: true
tags:
    - Ardupilot
---
## 前言
> 关于编译环境的具体搭建过程，参考官方文档手册：[官方文档](https://ardupilot.org/dev/docs/where-to-get-the-code.html)

## 环境参考
+ Ubuntu20.04
+ git
## 开始搭建
源代码的拉取、上传、获取子模块等操作需要用到git，网上的教程一大堆。我自己也并不太熟悉，就不讲解了<br>

1. 进入Ardupilot的官方git仓库：[官方仓库](https://github.com/Ardupilot/ardupilot.git)

2. Fork将其复制到自己的库中（没有账号的需要在github先建立一个自己的账号并登录）

3. 在本地文件夹下找一个位置当作工作空间，然后在终端中进入该文件夹下，将代码库克隆下来。
```bash
git clone https://github.com/your-github-account/ardupilot
```
4. 递归克隆子模块。因为Ardupilot中运用了一些其他的开源库等等，如轻量级的操作系统ChibiOS，用于通讯的mavlink，编译用的waf等<br>
这一段命令是将这个项目中所需要的子模块更新克隆下来，递归的意思是若子模块中包含了其他子模块，则一并克隆下来
```bash
cd ardupilot
sudo git submodule update --init --recursive
```
这段命令执行的时候对网络要求比较高，推荐的做法是：换源（希望你在安装系统的时候就已经做过了，推荐国内的清华源）
如果你还是失败了，可以将子模块一个一个手动下载下来，多试几次，将git://换成https://试试
5. 执行安装编译环境的自动化脚本
   ```bash
    Tools/environment_install/install-prereqs-ubuntu.sh -y
   ```
6. 这样可以先尝试编译一下，如果成功了那你运气真好，失败了可能才正常
    ```bash
    ./waf configure --board=sitl
    ./waf plane(编译固定翼部分代码)
    ```
如果失败了，或者之前某些步骤卡住了，可以参考我踩过的坑：
+ 如果第五步出问题：可能是你之前安装过的python版本与脚本中的不符。可以先查看你的python版本（应该是python3），然后打开脚本文件，搜索所有含pip和python的语句，将后面都加上一个3，就不会报错了
+ 如果编译报错：Could not find the program ['gcc-arm-none-eabi-ar']:我理解的原因为waf脚本在寻找gcc-arm-none-eabi-ar编译器的时候没找到。根据Ubuntu版本的不同，使用不同的编译器版本，相关的博客：[gcc-arm-none-eabi-ar编译器安装](https://blog.csdn.net/yk150915/article/details/80117082)，解决办法是正确设置环境变量，将软件包的/bin文件夹添加到环境变量中

设置环境变量的方法就是在隐藏文件.bashrc中添加export PATH=命令行路径:$PATH
或者修改/etc/profile文件


编译环境搭建好之后，可以通过命令将源码完成编译、上传等操作。简单介绍一下waf的常见命令使用
## waf常见命令使用
因为固件编译完需要上传到硬件上，所以需要先配置对应的硬件型号<br>
先查询一下可以支持哪些型号
```
./waf list_boards
```
找到你的板子对应的型号之后，进行配置(我的板子是SpeedyBeeF405WING)
```
./waf configure --board SpeedyBeeF405WING
```
Ardupilot的代码框架是由几种载具类型和共用库组成，几种车型分别为：
+ copter 多旋翼
+ plane  固定翼
+ antennatracker   循迹车
+ rover  车
编译的时候命令如下：
```
./waf copter
```
公共库中由很多example程序，都可以进行编译上传进行测试和对代码进行理解。<br>
查询有哪些example可以编译：
```
./waf list | grep 'examples'
```
编译对应的example程序
```
./waf --target examples/AP_AHRS
```
上传一个程序只需要后面加一个upload参数即可：<br>
编译RC输出的example程序并上传：
```
./waf --target examples/RCOutput --upload
```

更多的关于waf命令可以查看BUILD.md文件