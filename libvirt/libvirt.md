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
参考文档:
- [Creating a KVM virtual machine using CLI](https://www.rivy.org/2013/02/creating-a-kvm-virtual-machine/)
- [Domain XML format](https://libvirt.org/formatdomain.html)

`virsh` 构建于 `libvirt` 之上, 允许以 `shell` 方式使用 `libvirt` 功能.

- 创建磁盘镜像
  - `qemu-img create -f qcow2 [img_name].qcow2 10G`, -f 指定磁盘镜像格式为 `qcow2`
  - `qcow` 是 `QEMU` 使用的一种磁盘镜像文件格式, 全称是 `QEMU Copy on Write`. 它使用一种优化的磁盘分配策略, 一直延迟到真正使用时才分配存储空间. 改格式有两个版本, 分别是 `qcow` 与 `qcow2`.
  - 写时复制是指一个 `qcow` 文件可以共享作为 `base` 镜像中的数据, 只有需要修改时才把相应的数据拷贝过来. 在 `docker` 中也有这个概念.
  - 初始镜像大小只有大概 192 KB
    ```
    $ ls -l
    total 196
    -rw-r--r-- 1 tom tom 196624 Apr 16 20:45 centos.qcow2
    ```
- 使用 `xml` 文件定义 `domain`, 见 [domain_example](./domain_example.xml)
- 创建 `domain`
  ```
  $ virsh create domain_example.xml
  Domain CentOS_for_test created from domain_example.xml
  ```
- 列出 `domain`
  ```
  $ virsh list
   Id    Name                           State
  ----------------------------------------------------
   4     CentOS_for_test                running
  ```
- 挂起, 重启 `Domain`
  ```
  $ virsh suspend 4
  Domain 4 suspended

  $ virsh list
   Id    Name                           State
  ----------------------------------------------------
   4     CentOS_for_test                paused

  $ virsh resume 4
  Domain 4 resumed

  $ virsh list
   Id    Name                           State
  ----------------------------------------------------
   4     CentOS_for_test                running
  ```
- 连接 `Domain` 可以使用 `virt-manager`, 可以自动显示出已安装设备
  - 连接后会进入常见的系统安装流程
  - 安装成功后需要修改 `boot` 设备启动顺序, 将 `<boot dev='cdrom'/>` 改为 `<boot dev='hd'/>`.
  - 这一步既可以使用 `$ virsh edit [domain]` 修改 `xml` 配置; 也可以 `$ virsh destroy [domain]` 后, 再修改配置重新创建.
- 查看 `domain` `xml`格式信息  `virsh dumpxml [domain_name]`

### libvirt 和 Python
文档链接: [Libvirt Application Development Guide Using Python](https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/)

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

这段程序展示了如何通过 `libvirt` 获取 `domain` 信息. 要注意的是, 虽然 `libvirt` 提供了对多种语言的绑定, 但是 `api` 文档只针对了 `C` 语言. 要查看 `info()` 返回值的含义, 可以:
- 打开 `info()` 的定义, 找到对应的 `C` 函数为 `virDomainGetInfo`
  ```python
  def info(self):
    """Extract information about a domain. Note that if the connection used to get the domain is limited only a partial set of the information can be extracted. """
    ret = libvirtmod.virDomainGetInfo(self._o)
    if ret is None: raise libvirtError ('virDomainGetInfo() failed', dom=self)
    return ret
  ```
- 在 `domain` `api` 文档中查找该函数
  ```
  int virDomainGetInfo (virDomainPtr domain,
                        virDomainInfoPtr info)

  domain     a domain object
  info       pointer to a virDomainInfo structure allocated by the user
  Returns    0 in case of success and -1 in case of failure.
  ```
- `info` 信息定义在 `virDomainInfo` 中
  ```C
  struct virDomainInfo {
    unsigned char       state       // the running state, one of virDomainState
    unsigned long       maxMem      // the maximum memory in KBytes allowed
    unsigned long       memory      // the memory in KBytes used by the domain
    unsigned short      nrVirtCpu   // the number of virtual CPUs for the domain
    unsigned long long  cpuTime     // the CPU time used in nanoseconds
  }
  ```

## API 概述

## 使用 libvirt 的应用程序
文档连接: [Applications using libvirt](https://libvirt.org/apps.html)

- `OpenStack` 云操作系统, 即可用于公有云, 也可用于私有云. 它的多个组件管理着计算, 存储和网络资源, 并使用 `dashboard` 与用户交互. 其中的计算组件使用 `libvirt` 管理虚拟机的生命周期, 完成监控等操作.
- `collectd` `libvirt-plugin` 是它的一部分, 用于收集系统中虚拟客户机的统计数据. 通过该插件, 可以收集到每个客户机的 `CPU`, 网络接口和块设备的使用率, 而无需在客户机系统中安装 `collectd`.