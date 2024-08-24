---
layout:     post
title:      Solidworks方程式的使用
subtitle:   介绍了Solidworks中方程式功能的
date:       2024-02-01
author:     试墨临池
header-img: img/post_solidworks方程式.png
catalog: true
tags:
    - Solidworks
---

## 前言
> Solidworks中的方程式功能一般可能很少有人注意到。但是这样一个功能可以使得自顶向下设计如虎添翼。方程式的作用主要在于管理变量，方便数值的传递及修改。本文将完整的介绍一下方程式功能的使用

# 总体介绍

首先，新建项目后方程式的窗口在 工具->方程式
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/soliworks方程式窗口.png)

打开方程式窗口后发现左上角四个视图，分别为**方程式视图**、**草图方程式视图**、**尺寸视图**、**按序排列的视图**，作用如下：
+ 方程式视图：显示零件或装配体的所有全局变量和方程式。
+ 草图方程式视图：显示仅用于草图的全局变量和方程式。
+ 尺寸视图：显示用于活动草图、零件或装配体中的所有尺寸，包括带有设定值和由方程式所决定的尺寸。 
+ 按序排列的视图：按照求解顺序显示方程式和全局变量。

# 零件中方程式的使用

进入零件项目，一个数据通常在方程式视图中进行添加。若想为零件添加一个全局变量，可以在全局变量下方填入名称（如：凸台1高度等）、数值（常数）/方程式（可引用其他的变量的表达式）即可。<br>
而在使用的时候只需在相应的尺寸输入框中输入‘=’后 选择**全局变量**，在选择对应的名称即可。
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/1.png)
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/2.png)
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/3.png)

这样，在零件中可以随意使用方程式来进行零件中尺寸的关联了。<br>
需要注意的是，一般情况下但凡存在可以输入尺寸的地方都可以使用全局变量及方程式。并且，输入的尺寸也可以是全局变量的方程式或方程式的方程式。一个全局变量可以被反复引用，而当它被修改后，所有引用该全局变量的尺寸都会被更新。<br>

对话框右下角中的"链接至外部文件"可以将方程式配置保存到一个文本文件，或者从一个文本文件中读取方程式配置。（不过我觉得作用不大）。

# 装配体中方程式的使用

上述方法仅适用于单一文件中方程式的配置，但是对于一个装配体这样的对零件项目就不够完善。下面提供一个方法可以在零件之间或零件与装配体之间进行方程式或变量的引用<br>
首先打开装配体项目中的方程式对话框的方程式视图
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/装配体方程式窗口.png)
发现原本的方程式变成了两个 -顶层 与 -零部件，这个顾名思义即可。
若我在 *装配体1* 中添加了一个零件 *零件1*，并想要在零件1中引用装配体1的全局变量。
+ 首先在装配体1中添加一个全局变量
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/4.png)
+ 然后在与装配体同目录下的零件中引用变量（这里添加一个引用装配体1中的全局变量的全局变量为例）
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/5.png)
结果如下
![](https://raw.githubusercontent.com/shimolinchi/shimolinchi.github.io/master/img/2024-02-01Solidworks方程式的使用/6.png)
可以看到，零件中成功引用了装配体的变量。