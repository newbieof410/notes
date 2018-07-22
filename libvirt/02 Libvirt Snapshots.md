# Libvirt Snapshot
> 这里只翻译, 总结了原文的部分内容, 可以在这里 [查看原文 &raquo;](https://kashyapc.fedorapeople.org/virt/lc-2012/snapshots-handout.html)


## 简介
虚拟机快照是虚拟机 (包括其中的操作系统和应用) 在一个给定时间点的状态视图. 所以, 我们可以借助快照退回到虚拟机的一个正常状态, 或者在它运行时做一个备份. 在深入了解快照技术前, 我们先了解一下 `backing` 文件和 `overlay` 两个概念.

### QCOW2 backing files & overlays
从本质上讲, `QCOW2 (Qemu Copy-On-Write)` 使我们可以创建一个基础镜像 (也叫做 `backing` 文件), 并在其上创建多个可丢弃的, 写时复制的, 磁盘镜像的叠加层. 基础文件和叠加层在快速创建 `thin-provisioned` 虚拟机时十分有用 (下面会有更多介绍). 特别是在开发和测试环境中能发挥重要的作用, 使我们可以快速回退到一个已知状态, 丢弃掉覆盖层.

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
- 查看磁盘镜像信息
  ```
  $ qemu-img info [disk_img]
  ```
- 显示磁盘的所有依赖的基础镜像
  ```
  $ qemu-img info --backing-chain [disk_img]
  ```

### 快照技术术语
#### Internal snapshots
一个 `qcow2` 文件, 其中既存储着保存下来的状态, 也有自保存点以来的所有增量. 可以进一步划分为:
- **Internal disk Snapshot** 虚拟磁盘在一个特定时间点的状态. 快照信息和之后的增量 (后续修改) 信息都存储在同一个 `qcow2` 文件中. 在客户机 '在线' 和 '离线' 的两种状态下都能获取.
  - 客户机在线时, `libvirt` 使用 `qemu-img` 命令
  - 客户机离线时, 使用 `savevm` 命令
- **Internal system checkpoint** 一个运行中客户机的 `RAM` 状态, 设备状态和磁盘状态, 都存储在原有 `qcow2` 文件中. 可以在客户机运行时获取
  - 客户机在线时, `libvirt` 使用 `savevm` 命令

#### External snapshots
保存一个快照时, 保存的状态会被存储在一个文件 (它会成为一个只读的基础镜像文件) 中, 状态保存点之后的增量信息会保存在一个新的文件 (作为叠加层) 中. 进一步可分为:
- **External disk snapshot**
- **External system checkpoint**

#### VM State
将运行中的客户机 `RAM` 和设备状态 (不包括 `disk-state`) 存储到文件中, 可用于后续恢复系统状态. 类似于系统休眠操作.

#### 小结
内部快照和外部快照的一个区别是
- 快照保存下来的状态信息和增量信息是否存储在一个 `qcow2` 文件中

## 创建快照
当执行了创建外部快照的命令时, 会有一个新的叠加层被建立用于客户机的读写, 而之前的镜像则变为快照.

### 为磁盘创建内部快照
- 创建快照
  ```
  $ virsh snapshot-create-as overlay snap1 'first snapshot'
  Domain snapshot snap1 created
  ```
  其中:
  - `overlay` 是客户机名称
  - `snap1` 是快照名称
  - 最后的字符串是快照描述信息
- 列出快照, 并查看快照信息
 ```
 $ virsh snapshot-list overlay
  Name                 Creation Time             State
 ------------------------------------------------------------
  snap1                2018-04-18 11:20:22 +0800 shutoff
 $ qemu-img info overlay.qcow2
 image: overlay.qcow2
 file format: qcow2
 virtual size: 10G (10737418240 bytes)
 disk size: 19M
 cluster_size: 65536
 backing file: centos.qcow2
 Snapshot list:
 ID        TAG                 VM SIZE                DATE       VM CLOCK
 1         snap1                     0 2018-04-18 11:20:23   00:00:00.000
 Format specific information:
     compat: 1.1
     lazy refcounts: false
     refcount bits: 16
     corrupt: false
 ```

### 为磁盘创建外部快照
- 列出客户机关联的块设备
  ```
  $ virsh domblklist overlay
  Target     Source
  ------------------------------------------------
  hda        /home/tom/Projects/VirtMachine/IMGs/overlay.qcow2
  ```
- 创建磁盘外部快照 (在客户机仍在运行时)
  ```
  $ virsh snapshot-create-as --domain overlay snap2 'external-snap' --disk-only \
  > --diskspec hda,snapshot=external,\
  > file=/home/tom/Projects/VirtMachine/IMGs/sn1-of-overlay.qcow2 --atomic
  Domain snapshot snap2 created
  ```
  - `virsh` 命令及参数含义可以使用 `virsh help [keyword]` 查看
  - 这条命令执行后, `overlay` 的原始磁盘镜像会成为基础镜像文件, 另外会有一个新的叠加层被创建用以保存更改. 此后, `libvirt` 会使用这个叠加层进行写操作, 而把原来的镜像作为只读的基础镜像文件
- 查看客户机现在使用的块设备
  ```
  $ virsh domblklist overlay
  Target     Source
  ------------------------------------------------
  hda        /home/tom/Projects/VirtMachine/IMGs/sn1-of-overlay.qcow2
  ```

## 恢复快照状态

## 合并快照
外部快照用处很大. 但是, 外部快照多了之后, 维护和追踪这些独立的文件就成了新的问题. 这时, 我们可能希望合并一些快照文件, 以减少镜像链的长度. 有两种方式可帮我们达到这一目的:
- blockcommit: 把叠加层的数据合并到基础镜像文件中.
- blockpull: 把基础镜像中的数据合并到叠加层中.

### blockcommit
把上层文件数据向下层文件中合并. 这一操作完成后, 原先依赖上层镜像的部分, 会转而指向下层的文件.

```
.------------.  .------------.  .------------.  .------------.  .------------.
|            |  |            |  |            |  |            |  |            |
| RootBase   <---  Snap-1    <---  Snap-2    <---  Snap-3    <---  Snap-4    |
|            |  |            |  |            |  |            |  | (Active)   |
'------------'  '------------'  '------------'  '------------'  '------------'
                                 /                  |
                                /                   |
                               /  commit data       |
                              /                     |
                             /                      |
                            /                       |
                           v           commit data  |
.------------.  .------------. <--------------------'           .------------.
|            |  |            |                                  |            |
| RootBase   <---  Snap-1    |<---------------------------------|  Snap-4    |
|            |  |            |       Backing File               | (Active)   |
'------------'  '------------'                                  '------------'
```
上图展示了一条镜像链, 其中 `RootBase` 是基础镜像, 它有 4 个逐层依赖的外部快照, `Active` 表示当前的活动镜像层, 客户机的写操作在这一层完成. 下方箭头表示快照 2 和快照 3 将数据合并到了快照 1 中, 此后快照 1 就成了快照 4 的直接基础镜像.

```
.------------.  .------------.  .------------.  .------------.  .------------.
|            |  |            |  |            |  |            |  |            |
| RootBase   <---  Snap-1    <---  Snap-2    <---  Snap-3    <---  Snap-4    |
|            |  |            |  |            |  |            |  | (Active)   |
'------------'  '------------'  '------------'  '------------'  '------------'
                  /                  |             |
                 /                   |             |
                /                    |             |
   commit data /         commit data |             |
              /                      |             |
             /                       | commit data |
            v                        |             |
.------------.<----------------------|-------------'            .------------.
|            |<----------------------'                          |            |
| RootBase   |                                                  |  Snap-4    |
|            |<-------------------------------------------------| (Active)   |
'------------'                  Backing File                    '------------'
```
上图展示了另外一种情形, 这里快照 1, 2, 3 都合并到了根镜像, 成为活动镜像层直接基础镜像. 合并之后, 中间的镜像 1, 2, 3会成为无效镜像, 因为它们都依赖于根镜像的特定状态.

### blockpull
把下层文件的数据合并到上层, 合并的方向与 `blockcommit` 相反.

```
.------------.  .------------.  .------------.  .------------.  .------------.
|            |  |            |  |            |  |            |  |            |
| RootBase   <---  Snap-1    <---  Snap-2    <---  Snap-3    <---  Snap-4    |
|            |  |            |  |            |  |            |  | (Active)   |
'------------'  '------------'  '------------'  '------------'  '------------'
                         |                 |              \
                         |                 |               \
                         |                 |                \
                         |                 |                 \ stream data
                         |                 | stream data      \
                         | stream data     |                   \
                         |                 |                    v
     .------------.      |                 '--------------->  .------------.
     |            |      '--------------------------------->  |            |
     | RootBase   |                                           |  Snap-4    |
     |            | <---------------------------------------- | (Active)   |
     '------------'                 Backing File              '------------'
```
上图表示我们可以把快照 1, 2, 3 中的数据合并到活动镜像层, 使得 `RootBase` 成为活动镜像的直接基础镜像.

## 删除快照
