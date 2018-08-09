# 使用 tcpdump 抓取容器的网络通信

`tcpdump` 是 Linux 中一款常用的网络抓包工具, 可以展示出隐藏在背后的网络数据交换过程. 下面就以在默认网络连接方式下, 主机与容器的通信过程为例, 学习 `tcpdump` 的基本使用.

## 准备
首先, 要准备好一个安装了 `tcpdump`, `ip` 和 `ping` 这三个工具的容器. 如果主机中缺少相应的工具, 也是用同样的方法安装.

1.  编写 Dockerfile.

    ```dockerfile
    FROM ubuntu

    ENV REFRESHED_AT 2018-8-8

    RUN apt-get update
    RUN apt-get install -y tcpdump iproute2 iputils-ping
    ```

1.  构建镜像 `docker build -t tcpdump .`

1.  启动容器 `docker run -it tcpdump`

1.  检查容器 IP 地址

    - 找到容器 id 或名称 `docker ps`
    - 从容器信息中找到 IP `docker inspect <容器 id/name>`

## 主机访问容器
上一步得到的容器 IP 为 172.17.0.2. 现在使用 `ping` 命令模拟主机对容器的访问过程.

```
$ ping 172.17.0.2
```

在请求发送前, 先准备好 `tcpdump` 等待通信过程中的数据包. 启动命令如下.

```
$ sudo tcpdump -i docker0 arp or icmp
```

### 参数说明
`tcpdump` 的使用参数由两部分构成.

前一部分是基本选项, 设置了 `tcpdump` 的工作方式. 在上面的命令中使用了 `-i` 选项, 作用是指定 `tcpdump` 监听的网络接口. 因为容器默认采用 bridge 网络连接方式, 连接在 docker0 这一网络接口上, 所以主机到容器的信息一定会从这里经过, 也因此把它指定为了监听接口.

后一部分是过滤表达式, 用于把有用的网络包给筛选出来. `ping` 程序不同于常见的应用, 它不经过 TCP 或 UDP, 而是直接使用了网络层的 ICMP 协议. IP 数据包的传输依赖于链路层设备, 需要用到 ARP 协议将 IP 地址转换为 MAC 地址. 因此, 上面的过滤表达式就设置为 "筛选出协议类型为 ARP 或 ICMP 的数据包".

**Tips: ping**

`ping` 也是客户端 / 服务器程序. 当然发送的一端就是客户端了, 而被 `ping` 的一端则是服务器. 不过服务端程序是系统内核网络栈的一部分, 而不是单独的进程.

`ping` 程序使用 ICMP 请求服务器将请求回送回来, 从而计算数据包的往返时间.

### 输出分析
部分输出如下.

```
16:36:34.581999 ARP, Request who-has 172.17.0.2 tell abc, length 28
16:36:34.582039 ARP, Reply 172.17.0.2 is-at cc:cc:cc:cc:cc:cc (oui Unknown), length 28
16:36:34.582063 IP abc > 172.17.0.2: ICMP echo request, id 5892, seq 1, length 64
16:36:34.582094 IP 172.17.0.2 > abc: ICMP echo reply, id 5892, seq 1, length 64
16:36:35.611875 IP abc > 172.17.0.2: ICMP echo request, id 5892, seq 2, length 64
16:36:35.611956 IP 172.17.0.2 > abc: ICMP echo reply, id 5892, seq 2, length 64
```

在网络数据传输过程中, 不论上层使用了何种协议, 都要经过包装为 IP 数据包和封装为以太网帧两个步骤. 而在包装过程中必不可少的又是确定目标的地址. 包装 IP 数据包要使用的目标 IP 地址已经得到. 下面就来分析封装以太网帧所需要的 MAC 地址如何得到.


IP 层在收到数据包后要根据路由表选择发送方式.

```
$ ip route
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1
```

查找路由表, 找到发往目标网络 172.17.0.0/16 的数据包要从接口 docker0 发出. 接着从该接口发送 ARP 广播, 询问 172.17.0.2 的硬件地址.

输出的前两行正是 ARP 的询问过程. 之后便是 ICMP 的交互数据.

## 容器访问主机
容器访问主机的过程与上面类似. 这里需要打开两个容器终端, 一个用来 `ping`, 另一个使用 `tcpdump` 抓包.
```
$ docker exec -it <容器 id/name> bash
```

容器中默认只有两条路由信息, 所有对外的数据包都由 eth0 接口发出.
```
# ip r
default via 172.17.0.1 dev eth0
172.17.0.0/16 dev eth0  proto kernel  scope link  src 172.17.0.2
```

找到主机的 IP 地址为 222.xxx.xxx.xxx, 从容器中访问时会匹配到第一条默认路由.

在容器中准备好 `tcpdump`.
```
# tcpdump -i eth0 -e arp or icmp
```

这里使用了 `-e` 选项, 用来显示出数据包的 MAC 地址.

同时, 在主机中也打开 `tcpdump` 监听 docker0 接口. 现在开始从容器 `ping` 主机.

### 输出分析
容器中抓取到的数据包.
```
03:37:11.598177 cc:cc:cc:cc:cc:cc (oui Unknown) > bb:bb:bb:bb:bb:bb (oui Unknown), ethertype IPv4 (0x0800), length 98: xyz > 222.xxx.xxx.xxx: ICMP echo request, id 54, seq 1, length 64
03:37:11.598366 bb:bb:bb:bb:bb:bb (oui Unknown) > Broadcast, ethertype ARP (0x0806), length 42: Request who-has xyz tell 222.xxx.xxx.xxx, length 28
03:37:11.598401 cc:cc:cc:cc:cc:cc (oui Unknown) > bb:bb:bb:bb:bb:bb (oui Unknown), ethertype ARP (0x0806), length 42: Reply xyz is-at cc:cc:cc:cc:cc:cc (oui Unknown), length 28
03:37:11.598425 bb:bb:bb:bb:bb:bb (oui Unknown) > cc:cc:cc:cc:cc:cc (oui Unknown), ethertype IPv4 (0x0800), length 98: 222.xxx.xxx.xxx > xyz: ICMP echo reply, id 54, seq 1, length 64
```

主机中抓取到的数据包.
```
11:37:11.598195 cc:cc:cc:cc:cc:cc (oui Unknown) > bb:bb:bb:bb:bb:bb (oui Unknown), ethertype IPv4 (0x0800), length 98: 172.17.0.2 > abc: ICMP echo request, id 54, seq 1, length 64
11:37:11.598354 bb:bb:bb:bb:bb:bb (oui Unknown) > Broadcast, ethertype ARP (0x0806), length 42: Request who-has 172.17.0.2 tell abc, length 28
11:37:11.598404 cc:cc:cc:cc:cc:cc (oui Unknown) > bb:bb:bb:bb:bb:bb (oui Unknown), ethertype ARP (0x0806), length 42: Reply 172.17.0.2 is-at cc:cc:cc:cc:cc:cc (oui Unknown), length 28
11:37:11.598420 bb:bb:bb:bb:bb:bb (oui Unknown) > cc:cc:cc:cc:cc:cc (oui Unknown), ethertype IPv4 (0x0800), length 98: abc > 172.17.0.2: ICMP echo reply, id 54, seq 1, length 64
```

输出结果被作了简单的修改. 其中, `cc:cc:cc:cc:cc:cc` ,`bb:bb:bb:bb:bb:bb` 分别表示容器和 docker0 的 MAC 地址; `xyz` 为容器名, `abc` 为主机名.

第一个数据包由容器发往 docker0 从而到达主机. 在这个数据包发送前并未通过 ARP 获取主机 MAC 地址, 该参数可能在容器启动时就被写入了容器中.

第二, 三个数据包为主机通过 docker0 发送的 ARP 广播, 询问容器 MAC 地址.

第四个数据包是主机对容器发出的第一个 ICMP 请求的响应.

从上面的输出可以看到, 从主机到容器和从容器到主机两个方向的通信过程不是完全对称的. 主机向容器发送数据时, docker0 被当作网络接口, 与容器子网相连, 数据直接从该接口发出. 容器向主机发送数据时, docker0 被当作默认网关, 数据先被送到 docker0 再被转发.

## 容器访问外网
最后看一下容器访问外网的过程. 以访问百度服务器为例.

```
# ping www.baidu.com
```

启动容器中的 `tcpdump` 程序. 使用一些新的参数.
```
# tcpdump -i eth0 -net icmp
```
其中,
- `-n` 表示不做地址转换
- `-e` 表示输出 MAC 地址
- `-t` 不显示时间戳

并且这里只抓取 ICMP 数据包.

启动主机中的 `tcpdump` 程序.
```
$ sudo tcpdump -i any -net icmp
```
接口选项中的 `any` 表示获取所有接口数据.

### 输出分析
容器中得到的结果.
```
cc:cc:cc:cc:cc:cc > bb:bb:bb:bb:bb:bb, ethertype IPv4 (0x0800), length 98: 172.17.0.2 > 119.75.213.61: ICMP echo request, id 66, seq 1, length 64
bb:bb:bb:bb:bb:bb > cc:cc:cc:cc:cc:cc, ethertype IPv4 (0x0800), length 98: 119.75.213.61 > 172.17.0.2: ICMP echo reply, id 66, seq 1, length 64
```

与普通数据包传输过程相同. 向 docker0 发出请求, 再从 docker0 得到响应.

主机中得到的结果.
```
P cc:cc:cc:cc:cc:cc ethertype IPv4 (0x0800), length 100: 172.17.0.2 > 119.75.213.61: ICMP echo request, id 66, seq 1, length 64
In cc:cc:cc:cc:cc:cc ethertype IPv4 (0x0800), length 100: 172.17.0.2 > 119.75.213.61: ICMP echo request, id 66, seq 1, length 64
Out hh:hh:hh:hh:hh:hh ethertype IPv4 (0x0800), length 100: 222.xxx.xxx.xxx > 119.75.213.61: ICMP echo request, id 66, seq 1, length 64
In 00:74:9c:92:27:42 ethertype IPv4 (0x0800), length 100: 119.75.213.61 > 222.xxx.xxx.xxx: ICMP echo reply, id 66, seq 1, length 64
Out bb:bb:bb:bb:bb:bb ethertype IPv4 (0x0800), length 100: 119.75.213.61 > 172.17.0.2: ICMP echo reply, id 66, seq 1, length 64
Out bb:bb:bb:bb:bb:bb ethertype IPv4 (0x0800), length 100: 119.75.213.61 > 172.17.0.2: ICMP echo reply, id 66, seq 1, length 64
```

主机的处理过程就复杂一些了. 大致过程如下.

前两个数据包表示主机接收到从容器发来的数据.

第三条记录. 检查数据包目的地址发现不是本机, 需要转发. 转发时修改了数据包的源地址, 即作了源地址转换. 主机在这里发挥了路由器的功能.

在第四条记录中, 主机收到了由目的地址发来的响应.

最后两条记录都表示响应经过转换后由 docker0 送回容器.

## 总结
上面观察了容器通信的三种情形, 看到了数据的具体传递过程, 同时也对 `tcpdump` 的使用有了一定的了解. 简单总结一下见到的用法.

```
$ sudo tcpdump -i eth0 -net arp or icmp
```
选项:
- `-i` 选择监听的接口, `any` 表示所有接口
- `-net` 不带参数, 分别控制名称转换, MAC 地址和时间戳
过滤表达式:
- `arp` 和 `icmp` 表示监听的协议, 多个表达式可以通过逻辑连接词连接

此外, 还见到了打开多个容器终端的方法.

```
$ docker exec -it <容器 id/name> bash
```

常用的网络工具和对应的软件包分别是:
- `tcpdump`: tcpdump
- `ip`: iproute2
- `ping`: iputils-ping

在最后的主机输出中还有一个问题没有解决. 第一行的 `P` 代表什么? 为什么前两行和后两行都是相同的两条数据?

## 参考资料
- [Manpage of TCPDUMP](http://www.tcpdump.org/manpages/tcpdump.1.html)
- [Manpage of PCAP-FILTER](http://www.tcpdump.org/manpages/pcap-filter.7.html)
