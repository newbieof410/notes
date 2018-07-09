# libvirt

`libvirt` 提供了客户机管理 `API`, 起初为 `XEN` 设计,  后被拓展到多种虚拟机管理程序.

## 简介

`libvirt` 中的几个重要概念:
- **Node**  指物理机, 上面可以运行多个虚拟客户机.
- **Hypervisor** aka Virtual Machine Monitor.
- **Domain** aka instance, 运行在 Hypervisor 上的客户机操作系统实例.

提供的管理功能:
- **域管理** 包括对域的生命周期的管理, 如启动, 停止, 暂停; 还包括对多种设备的热插拔操作, 如磁盘, 网卡, 内存和 CPU.
- **远程节点管理** 被管理的节点上需运行有 libvirtd 守护进程, 支持多种网络远程传输类型.
- **存储管理**
- **网络管理**
- **稳定, 可靠, 高效的应用程序接口, 用于完成上面的管理功能**

主要组成部分:
- **应用程序编程接口库** 为虚拟机管理程序, 如 virt-manager 提供虚拟机管理的程序库支持.
- **守护进程 libvirtd** 负责执行对节点上域的管理工作.
- **virsh** libvirt 默认的虚拟机管理命令行工具.

## 基本架构
<div align="center"> <img src="https://www.ibm.com/developerworks/cn/linux/l-libvirt/figure1.gif" /> </div><br>

## 控制方式
在上图中, 虚拟机管理程序和被管理的 `Domain` (或称 `guest`) 运行在同一`Node` (`host`)上, 这是其中一种工作方式.

此外, 管理程序还可以位于不同的结点上, 通过网络调用远程结点上的 `libvirtd`, 达到管理的目的.

在结点上安装 `libvirt` 时, `libvirtd` 会自动启动, 并为结点上的虚拟机监控程序安装驱动程序.

<div align="center"> <img src="https://www.ibm.com/developerworks/cn/linux/l-libvirt/figure2.gif"/> </div><br>

## 对虚拟机监控程序的支持
`libvirt` 采用一种基于驱动程序的架构, 提供一种通用的 `api`, 以通用的方式为不同的虚拟机管理程序提供支持.

不同的虚拟机监控程序毕竟存在差异, 对于某些虚拟机监控程序专有的功能, `libvirt` 并未提供完全的支持, 虚拟机监控程序也可能不具备 `libvirt` 中定义的某些功能.

<div align="center"> <img src="https://www.ibm.com/developerworks/cn/linux/l-libvirt/figure3.gif" /> </div><br>

## libvirt 和 virsh

`virsh` 构建于 `libvirt` 之上, 允许以 `shell` 方式使用 `libvirt` 功能.

下面介绍一种通过 `virsh` 创建虚拟机的方式, 包括以下步骤:
1. 创建磁盘镜像文件;
1. 创建虚拟机配置文件, 将第一步的镜像文件作为虚拟机磁盘;
1. 使用配置文件创建虚拟机;
1. 连接虚拟机进行系统安装或使用;

### 创建磁盘镜像
`qemu-img create -f qcow2 [img_name].qcow2 10G`.
- `-f` 指定磁盘镜像格式为 `qcow2`

**注:**
- `qcow` 是 `QEMU` 使用的一种磁盘镜像文件格式, 全称是 `QEMU Copy on Write`. 它使用一种优化的磁盘分配策略, 一直延迟到真正使用时才分配存储空间. 该格式有两个版本, 分别是 `qcow` 与 `qcow2`.
- 写时复制是指一个 `qcow` 文件可以共享作为 `base` 镜像中的数据, 只有需要修改时才把相应的数据拷贝过来. 在 `docker` 中也有这个概念.
- 虽然创建时指定的大小为 10G, 但初始镜像大小只有大概 192 KB.
  ```
  $ ls -l
  total 196
  -rw-r--r-- 1 tom tom 196624 Apr 16 20:45 centos.qcow2
  ```

### 创建配置文件

`libvirt` 使用 `xml` 文件对虚拟机进行配置. 示例, [domain_example.xml](./01-2%20domain_example.xml).

### 创建虚拟机
```
$ virsh create domain_example.xml
Domain CentOS_for_test created from domain_example.xml
```
直接 `create` 出的虚拟机在该虚拟机关机后会消失, 要保留该虚拟机可以先 `define` 再 `start`.

### 连接虚拟机
最后要使用虚拟机还要先进行连接, 这里提供两种方式.

1. `virt-manager` 是一个虚拟机的图形界面管理工具, 可以自动找到已安装的虚拟机, 那么在工具中打开新创建的虚拟机就可以了;
1. 或者使用命令行工具 `virt-viewer`.
  ```shell
  $ virt-viewer <domain>
  ```

连接到虚拟机后会进入系统安装流程, 这与配置文件中的设置有关:
- 在配置文件中, 系统启动设备的设置
  ```xml
  <os>
      <boot dev='cdrom'/>
  </os>
  ```
- `cdrom` 的具体设置
  ```xml
  <devices>
      <disk type='file' device='cdrom'>
          <source file='/home/tom/Projects/VirtMachine/ISOs/CentOS-7-x86_64-Minimal-1708.iso'/>
          <target dev='hdb' bus='ide'/>
      </disk>
  </devices>
  ```

这里的设置与我们给物理机安装系统的过程类似: 将系统盘放入光驱, 在开机时设置为从光驱启动.

系统安装成功后就可以把系统盘取出来了. 具体操作为修改 `boot` 设备启动顺序, 将 `<boot dev='cdrom'/>` 改为 `<boot dev='hd'/>`.

这一步的更改有两种方式完成:
1. 使用 `$ virsh edit <domain>` 修改 `xml` 配置;
1. 也可以使用 `$ virsh destroy <domain>` 删除掉当前的虚拟机, 再修改配置重新创建. 在执行这一步时, 前面创建的磁盘镜像中已经安装好了系统, 所以可以跳过安装过程.

### virsh 的其他操作

虚拟机可以通过 `id` 或 `name` 两种方式指定.
- 列出 `domain`
  ```shell
  $ virsh list
   Id    Name                           State
  ----------------------------------------------------
   4     CentOS_for_test                running
  ```

- 挂起
  ```shell
  $ virsh suspend 4
  Domain 4 suspended

  $ virsh list
   Id    Name                           State
  ----------------------------------------------------
   4     CentOS_for_test                paused
  ```

- 重启
  ```shell
  $ virsh resume 4
  Domain 4 resumed

  $ virsh list
   Id    Name                           State
  ----------------------------------------------------
   4     CentOS_for_test                running
  ```

- 查看 `domain` 配置信息
  ```shell
  $ virsh dumpxml <domain>
  ```

## libvirt 和 Python

`libvirt` 提供了对多种语言的绑定, 在 `Python` 中使用需要安装 `libvirt-python` 软件包.

```Python
import libvirt


class LibvirtKVM:

    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = libvirt.open('qemu:///system')

        return self._conn

    def list_dom_id(self):
        try:
            dom_ids = self.conn.listDomainsID()
        except libvirt.libvirtError as e:
            print(e)
            return

        for dom_id in dom_ids:
            yield dom_id

    def dom_info(self, id):
        try:
            dom = self.conn.lookupByID(id)
        except libvirt.libvirtError as e:
            print(e)
            return

        state, maxmem, mem, cpus, cput = dom.info()
        print('The state is ' + str(state))
        print('The max memory is ' + str(maxmem))
        print('The memory is ' + str(mem))
        print('The number of cpus is ' + str(cpus))
        print('The cpu time is ' + str(cput))


if __name__ == '__main__':
    test = LibvirtKVM()

    for domain in test.list_dom_id():
        test.dom_info(domain)
```

这段程序展示了如何通过 `libvirt` 获取 `domain` 信息.

要注意的是, 虽然 `libvirt` 提供了多种语言的绑定, 但是只有 `C` 语言的配套文档. 虽然语言间存在差异, 但是函数返回值的含义应当是相同的.

以函数 `info()` 为例, 可以通过下面的方式查看函数返回值含义.

1.  打开 `info()` 的定义, 找到对应的 `C` 函数为 `virDomainGetInfo`;
    ```python
    def info(self):
      """Extract information about a domain. Note that if the connection used to get the domain is limited only a partial set of the information can be extracted. """
      ret = libvirtmod.virDomainGetInfo(self._o)
      if ret is None: raise libvirtError ('virDomainGetInfo() failed', dom=self)
      return ret
    ```

1.  在 `domain api` 文档中查找该函数;
    ```
    int virDomainGetInfo (virDomainPtr domain,
                          virDomainInfoPtr info)

    domain     a domain object
    info       pointer to a virDomainInfo structure allocated by the user
    Returns    0 in case of success and -1 in case of failure.
    ```

1.  `info` 信息没有直接返回, 而是保存在了在 `virDomainInfo` 结构体中, 定义如下.
    ```C
    struct virDomainInfo {
      unsigned char       state       // the running state, one of virDomainState
      unsigned long       maxMem      // the maximum memory in KBytes allowed
      unsigned long       memory      // the memory in KBytes used by the domain
      unsigned short      nrVirtCpu   // the number of virtual CPUs for the domain
      unsigned long long  cpuTime     // the CPU time used in nanoseconds
    }
    ```

## 使用 libvirt 的应用程序

- `OpenStack` 云操作系统, 即可用于公有云, 也可用于私有云. 它的多个组件管理着计算, 存储和网络资源, 并使用 `dashboard` 与用户交互. 其中的计算组件使用 `libvirt` 管理虚拟机的生命周期, 完成监控等操作.
- `collectd` `libvirt-plugin` 是它的一部分, 用于收集系统中虚拟客户机的统计数据. 通过该插件, 可以收集到每个客户机的 `CPU`, 网络接口和块设备的使用率, 而无需在客户机系统中安装 `collectd`.
- etc.

## 参考资料
- [Libvirt 虚拟化库剖析](https://www.ibm.com/developerworks/cn/linux/l-libvirt/)
- [Creating a KVM virtual machine using CLI](https://www.rivy.org/2013/02/creating-a-kvm-virtual-machine/)
- [Domain XML format](https://libvirt.org/formatdomain.html)
- [Libvirt Application Development Guide Using Python](https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/)
- [Applications using libvirt](https://libvirt.org/apps.html)
