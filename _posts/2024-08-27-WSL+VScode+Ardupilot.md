---
layout:     post
title:      在wsl上配置Ardupilot编译环境，并用VScode进行开发
subtitle:   wsl + vscode + ardupilot + stm32CubeProgrammer
date:       2024-08-27
author:     试墨临池
header-img: img/post_ROS.png
catalog: true
tags:
    - WSL
    - Ardupilot
    - Ubuntu
---
## 前言
> 之前在Ubuntu系统上编译，发现太麻烦了，每次都要重启。因此我尝试用WSL重新配一个环境。WSL有一些不完善的地方，例如串口的使用很不方便，后面我会给出我的解决办法。

# WSL的安装
安装的过程十分简单，具体可以查看[官方文档](https://learn.microsoft.com/zh-cn/windows/wsl/install)

安装的要求是window10以上，我的是win11。

开始安装：
+ win+R输入cmd打开命令行，或者直接搜索powershell
+ wsl --install
+ 重启
+ 开启相关配置：
  + 打开控制面板
  + 搜启用或关闭windows功能
  + 将**虚拟机平台** 和 **适用于 Linux 的 Windows 子系统** 勾选上
+ 进入命令行，点击上方的向下小箭头就可以打开Ubuntu的终端了
+ 配置用户名和密码

win11默认安装的WSL为wsl2版本，Ubuntu版本为22.04，如果安装其他版本需要参考官方手册。<br>
现在wsl基本安装完了，不过还需要进行代理的配置。不然不能与主机localhost共享代理端口，而且每次新建终端都会提示你：检测到 localhost 代理配置，但未镜像到 WSL

+ 在C://user/你的用户名/ 下新建一个无扩展名文件（不能是.txt）
+ 将文件命名为.wslconfig
+ 向文件中添加这些：
```
[experimental]
autoMemoryReclaim=gradual
networkingMode=mirrored
dnsTunneling=true
firewall=true
autoProxy=true
```
+ 保存，重新进入Ubuntu，发现不会提示报错了。

这里无扩展名的文件建立方法直接右键创建文本文档是不行的，我的方法是在vscode中新建文件比较容易

# VScode

安装了wsl后，Ubuntu系统可以直接享用windows中的VScode。windows下载个VScode轻而易举，只需要新安装一个插件即可使用。
+ 插件搜索：WSL,安装插件
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-08-27-WSL+VScode+Ardupilot/1.png)
+ 选择左边的远程资源管理器，直接打开Ubuntu中项目对应的文件夹即可

# Ardupilot编译环境搭建

先上[官方文档](https://ardupilot.org/dev/docs/building-setup-windows11.html)

克隆代码什么的都一样，可以参考之前的文章：
[Ardupilot编译环境搭建](http://wangrui.tech/2024/07/03/Ardupilot%E7%BC%96%E8%AF%91%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA/)

这里直接讲坑

1. ![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-08-27-WSL+VScode+Ardupilot/2.png)
   看来是子模块路径找不到了，直接输入提示的命令就行
2. ![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-08-27-WSL+VScode+Ardupilot/3.png)
   应该是用户权限不够了。先看看用户权限是什么：
   ```
   ls -l /home/wangrui/Ardupilot/ardupilot/.git/modules/modules/
   ```
   发现这个文件夹属于root，那就更改一下用户所有权：
  ```
    sudo chown -R wangrui:wangrui /home/wangrui/Ardupilot/ardupilot/.git/modules/modules/
  ```
这我一下将所有子模块的所有权全变成当前用户了，因为报错的这一个只是特例，要是只改ChibiOS这一个文件夹，后面还要改好多次。因此直接将子模块所有权设置就可以。

或者直接删锁文件：
```
sudo rm /home/wangrui/Ardupilot/ardupilot/.git/modules/modules/ChibiOS/config.lock
```

3. ![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-08-27-WSL+VScode+Ardupilot/4.png)
好眼熟，又是老问题，直接配环境变量就可以。直接转到/opt/gcc-arm-none-eabi-10-2020-q4-major/bin，然后export PATH=$PATH:/opt/gcc-arm-none-eabi-10-2020-q4-major/bin

# 上传程序

当我像以往一样 ./waf plane --upload 的时候，我不知道我正走入了深渊
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-08-27-WSL+VScode+Ardupilot/5.png)
第一个问题，看起来还好办。就是找不到serial包了，我重新安装然后在源代码中import serial前面添加了引入环境变量。就是在//wsl.localhost/Ubuntu/home/wangrui/Ardupilot/ardupilot/Tools/scripts/uploader.py
中添加sys.path.append('/usr/lib/python3/dist-packages')。

报错没了，但问题还在。我插上板子，发现怎么拔插也没法正常擦除上传程序。

回过头去查看官方文档，发现wsl不能正常使用windows串口，需要安装一个第三方软件[usbipd](https://github.com/dorssel/usbipd-win/releases)。
然后就下载安装，进行配置。

+ 首先查看串口
  ```
  usbipd list
  ```
+ 找到对应的串口编号（如1-1，2-2，写在最左边）
+ 绑定串口
  ```
  usbipd bind --busid 4-4
  ```
+ 连接串口到wsl
  ```
  usbipd attach --wsl --busid 4-4
  ```
+ 在Ubuntu中查看
  ```
  lsusb
  ```

还有需要用到的命令，
解绑串口
```
usbipd unbind --busid 4-4
```
取消连接
```
usbipd detach --busid 4-4
```

串口确实绑定到了wsl上，也能检测到。甚至通过screen接收数据都没问题，但仍然传不了程序。我又看了一遍官方文档，发现有这么一句：As of July 2022, Microsoft’s solution of providing USB access to WSL2 via usbipd does not work for accessing the bootloader on the device due to slow mounting times.（截至 2022 年 7 月，由于挂载时间缓慢，Microsoft 通过 usbipd 为 WSL2 提供 USB 访问的解决方案不适用于访问设备上的引导加载程序。）

这下心凉了

不过不用wsl传程序，还可以用其他办法传嘛，比如地面站。之前我用betaflight、MissionPlanner都挺难传上的，但是用[stm32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html)亲测可以

烧录的时候一定要进入DFU模式，即按住boot键再插电源。如果设备管理器中通用串行总线设备中能检测到就能直接连上。选择USB
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-08-27-WSL+VScode+Ardupilot/6.png)

左边点击打开文件，选择wsl编译出来的固件文件（一定要选with_bl的），加载文件，然后download就可以了

等一会烧录进去可以连上地面站，没啥问题