# libvirt 虚拟化库剖析
[原文地址](https://www.ibm.com/developerworks/cn/linux/l-libvirt/)

- 客户机管理 `API`.
- 起初为 `XEN` 设计,  后被拓展到管理多种操作系统

## 基本架构
![](https://www.ibm.com/developerworks/cn/linux/l-libvirt/figure1.gif)

### 控制方式
- 在上图中, 虚拟机管理程序和被管理的 `Domain` (或称 `guest`) 运行在同一`Node` (`host`)上, 这是其中一种工作方式.
- 此外, 管理程序还可以位于不同的结点上, 通过网络调用远程结点上的 `libvirtd`, 达到管理的目的.
- 在结点上安装 `libvirt` 时, `libvirtd` 会自动启动, 并为结点上的虚拟机监控程序安装驱动程序.

![](https://www.ibm.com/developerworks/cn/linux/l-libvirt/figure2.gif)

### 对虚拟机监控程序的支持
- `libvirt` 采用一种基于驱动程序的架构, 提供一种通用的 `api`, 以通用的方式为不同的虚拟机管理程序提供支持.
- 不同的虚拟机监控程序毕竟存在差异, 对于某些虚拟机监控程序专有的功能, `libvirt` 并未提供完全的支持, 虚拟机监控程序也可能不具备 `libvirt` 中定义的某些功能.

![](https://www.ibm.com/developerworks/cn/linux/l-libvirt/figure3.gif)

## 使用示例
介绍 `libvirt` 的基本使用
### libvirt 和 virsh
- `virsh` 构建于 `libvirt` 之上, 允许以 `shell` 方式使用 `libvirt` 功能.
- `virsh` 基本操作
  - 定义 `Domain` 配置文件
  - 启动 `Domain`
  - 列出 `Domain`
  - 挂起, 重启 `Domain`
  - 连接 `Domain`

### libvirt 和 Python

## API 概述

## 使用 libvirt 的应用程序
[文档连接](https://libvirt.org/apps.html)
- `OpenStack` 云操作系统, 即可用于公有云, 也可用于私有云. 它的多个组件管理着计算, 存储和网络资源, 并使用 `dashboard` 与用户交互. 其中的计算组件使用 `libvirt` 管理虚拟机的生命周期, 完成监控等操作.
- `collectd` `libvirt-plugin` 是它的一部分, 用于收集系统中虚拟客户机的统计数据. 通过该插件, 可以收集到每个客户机的 `CPU`, 网络接口和块设备的使用率, 而无需在客户机系统中安装 `collectd`.
