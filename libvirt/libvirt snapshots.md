# Libvirt Snapshot
[原文地址](https://kashyapc.fedorapeople.org/virt/lc-2012/snapshots-handout.html)

## 简介
虚拟机快照是虚拟机 (包括其中的操作系统和应用) 在一个给定时间点的状态视图. 所以, 我们可以借助快照退回到虚拟机的一个正常状态, 或者在它运行时做一个备份. 在深入了解快照技术前, 我们先了解一下 `backing` 文件和 `overlay` 两个概念.

### QCOW2 backing files & overlays
从本质上讲, `QCOW2 (Qemu Copy-On-Write)` 使我们可以创建一个基础镜像 (也叫做 `backing` 文件), 并在其上创建多个可丢弃的, 写时复制的, 磁盘镜像的叠加层. 基础文件和叠加层在快速创建 `thine-provisioned` 虚拟机时十分有用 (下面会有更多介绍). 特别是在开发和测试环境中能发挥重要的作用, 使我们可以快速回退到一个已知状态, 丢弃掉覆盖层.

```
.--------------.    .-------------.    .-------------.    .-------------.
|              |    |             |    |             |    |             |
| RootBase     |<---| Overlay-1   |<---| Overlay-1A  <--- | Overlay-1B  |
| (raw/qcow2)  |    | (qcow2)     |    | (qcow2)     |    | (qcow2)     |
'--------------'    '-------------'    '-------------'    '-------------'
```
在上图中, 每层镜像都构建在前一层之上.
```
.-----------.   .-----------.   .------------.  .------------.  .------------.
|           |   |           |   |            |  |            |  |            |
| RootBase  |<--- Overlay-1 |<--- Overlay-1A <--- Overlay-1B <--- Overlay-1C |
|           |   |           |   |            |  |            |  | (Active)   |
'-----------'   '-----------'   '------------'  '------------'  '------------'
   ^    ^
   |    |
   |    |       .-----------.    .------------.
   |    |       |           |    |            |
   |    '-------| Overlay-2 |<---| Overlay-2A |
   |            |           |    | (Active)   |
   |            '-----------'    '------------'
   |
   |
   |            .-----------.    .------------.
   |            |           |    |            |
   '------------| Overlay-3 |<---| Overlay-3A |
                |           |    | (Active)   |
                '-----------'    '------------'
```
上图是为了说明使用一个基础镜像, 可以创建多个叠加层供后续使用.
**NOTE**
- 基础文件只会以只读的方式打开. 换句话说, 一旦创建了叠加层, 就不能再修改它的基础文件.

**Example**
```
[FedoraBase.img] ----- <- [Fedora-guest-1.qcow2] <- [Fed-w-updates.qcow2] <- [Fedora-guest-with-updates-1A]
                 \
                  \--- <- [Fedora-guest-2.qcow2] <- [Fed-w-updates.qcow2] <- [Fedora-guest-with-updates-2A]
```
图中每层镜像的箭头指向它的基础镜像

在上面的例子中, 假设在 `FedoraBase.img` 中新装了 `Fedora` 系统, 然后把它作为我们的基础镜像文件. 现在, 就能创建 `QCOW2` 叠加层文件指向基础镜像, 新建两个简单配置 (`thinly provisioned`) 的 `Fedora` 客户机, 相当于把基础镜像作为了创建系统的模板. 上面也展示了一个基础根镜像可用于创建多个叠加层.

下面就使用 `centos.qcow2` 作为基础镜像, 在这之上创建 1 个叠加层, 并用它创建一个虚拟机.
- 创建叠加层
 ```
 $ qemu-img create -b centos.qcow2 -f qcow2 centos-overlay-1.qcow2
Formatting 'centos-overlay-1.qcow2', fmt=qcow2 size=10737418240 backing_file=centos.qcow2 cluster_size=65536 lazy_refcounts=off refcount_bits=16
 ```
- 在 `domain_example.xml` 文件的基础上, 修改 `disk` 中的 `source` 标签, 指向新的镜像文件
 ```xml
 <source file='/home/tom/Projects/VirtMachine/IMGs/centos-overlay-1.qcow2'/>
 ```
- 创建虚拟机 `virsh create domain_example.xml`
- 进入虚拟机创建文件
  ```
  $ touch overlay-1
  $ echo 'Add this file in overlay-1' >> overlay-1
  ```
- 重复上述过程, 在 `centos-overlay-1.qcow2` 上再创建一个叠加层, 并启动一个虚拟机. **这一步出现错误, 无法创建虚拟机** 但是可以确定在叠加层能够使用基础镜像中的文件.
