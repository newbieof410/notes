# Socket Basics
- 通过 `socket` 模块可以直接访问操作系统提供的 BSD socket 接口.
- socket 是连接的一个端点, 包含 IP 地址和端口号.
- 一个 TCP 连接有两个端点, 所以一个 socket 不能代表连接, 必须同时得到处于连接两端的一对 socket. 也就是说连接至少包含四项信息:
  ```
  (client IP, client port, server IP, server port)
  ```
- socket 既可以用于同一台设备中的不同进程间通信, 也可用于不同设备中的进程间通信.

## 创建 socket
创建 socket 通常只要提供两个参数:
```python
sock_obj = socket.socket(family, type)
```

其中,
- `family` 表示使用的地址或协议类型.
  - `AF_NET` 表示使用 IPv4 地址.
- `type` 表示通信方式.
  - `SOCK_STREAM` 表示使用 TCP 协议,
  - `SOCK_DGRAM` 表示使用 UDP 协议.

创建过程中的异常通过 `socket.error` 捕获.

## 客户端
客户端程序的一般操作为:
1. 创建 socket;
1. 初始化连接;
1. 收发数据;
1. 关闭连接.

**示例**

```python
import socket

host = 'www.baidu.com'
port = 80

ip = socket.gethostbyname(host)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((ip, port))
    s.sendall(b'GET / HTTP/1.1\r\n\r\n')
    print(s.recv(1024).decode())
```
- `SOCK_STREAM` 类型的 socket 要先使用 `connect()` 方法建立到 IP 和 port 的连接.
- 通过尝试连接服务器的不同的端口, 可以检查哪些端口处于开放状态.
- `gethostbyname()` 相当于 DNS 客户端.
- 接收数据的方法 `recv()` 会处于阻塞状态, 直到设置的缓冲空间被填满.

## 服务端
服务端程序的一般操作为:
1. 创建 socket;
1. 绑定至一个地址;
1. 等待连接请求;
1. 接受请求, 建立连接;
1. 收发数据;
1. 关闭连接.

**示例**

```python
import socket

HOST = ''
PORT = 8080
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print('Serving HTTP on port %s ...' % PORT)
    while True:
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            print(conn.recv(1024).decode())
            conn.sendall(b'Hello!')
```
- `bind()` 用来把 socket 与一个地址绑定, 这样网络协议栈在收到发给这个地址的数据时, 就知道应该交给当前程序处理.
- `listen()` 表示服务器已经准备好处理连接, 它的参数 `backlog` 代表等待服务的连接队列长度.
- `accept()` 接受连接, 返回一个新的 socket 表示完整的连接, 和客户端地址.
- 服务端 socket 的接收缓冲区同样是有限的, 如果服务端处理得比较慢, 发送数据的客户端会进入阻塞状态.

## backlog
在服务器接收连接的过程中使用了 `listen([backlog])` 方法, 它接受一个可选的默认值参数. 关于该参数, 文档中作了如下描述:

>  If backlog is specified, it must be at least 0 (if it is lower, it is set to 0); it specifies the number of unaccepted connections that the system will allow before refusing new connections. If not specified, a default reasonable value is chosen.

只有这几句解释还是不足以说明这个参数究竟起到怎样的作用. 为了把这里理清楚, 必须从原理上对 TCP 请求有一定了解.

**Tips: 为什么叫 BSD socket 接口?**

在各种编程语言中, 都提供了用于网络编程的 `socket` 库函数. 但是语言本身并不提供网络协议栈的实现, 因为这是操作系统功能的一部分, 语言只是提供了对系统接口的调用方法.

最早的网络协议栈来自伯克利大学的 Unix 发行版 (BSD), 同时期虽然还有许多类型的操作系统, 但是经过标准化组织的努力, 制定了 Posix 等 Unix 标准, 使得不同发行版的系统调用接口可以相互兼容, 甚至在 Window 和 MacOS 上都可以使用.

### 服务器处理过程

这里说的服务器是软件服务器, 而不是指硬件设备. 它与客户端的通信建立在网络协议栈之上. 通信所需的连接由系统网络协议栈提供, 根据端口号协议把连接分发给应用程序, 或者服务器进行处理. 所以服务器无需关心连接的建立过程, 它所得到的连接已经经过三次握手, 可以直接收发数据.

示例中的服务器在单一进程中工作, 只有当服务完上一个用户请求后才能处理下一个请求. 这样显然太慢了. 实际的服务器往往会创建多个线程或进程来提高并发处理能力. 但是这样就能保证新到来的请求能被服务器程序及时处理吗? 不能. 对于这部分请求, 性能瓶颈在服务器的处理能力. 虽然已经建立起连接, 但却得不到及时处理.

操作系统提供了一个队列来保存尚未得到处理的连接, 这个队列的长度就由应用程序中的 `backlog` 指定. 但是 `backlog` 并不能任意大, 它是一个大小受限的系统参数. 在 Linux 系统中的查看方式为:
```shell
$ cat /proc/sys/net/core/somaxconn
128
```
这里系统设置的长度上限为 128.

当 `backlog` 队列已满, 系统继续收到客户端请求时, 默认会不响应客户端的 `SYN` 请求. 这就迫使客户端超时重传. 如果重传后队列腾出了空间, 那么连接顺利建立, 否则继续重试, 最终被客户端确定为超时错误.

不过还有一个 `tcp_abort_on_overflow` 选项, 如果被启用, 当处理不了新的连接时, 会向客户端发送 `RST` 报文.

```shell
$ cat /proc/sys/net/ipv4/tcp_abort_on_overflow
0
```
该选项接收一个 boolean 值, 默认处于关闭状态.

### 观察服务过程
下面通过观察服务过程中网络连接信息的变化来进一步理解 `backlog` 的作用.

在测试过程中需要使用到 `telnet` 建立与服务器的连接, 服务器仍然使用示例程序, 另外还需要 `netstat` 观察网络信息.

**netstat 基本使用**

`netstat` 可以用于显示网络连接, 路由表, 网络接口等多个维度的网络信息. 但是在接下来的测试中, 只需要使用其中的三个参数:
- `-a`, 显示处于所有状态下的 socket 信息
- `-n`, 不作域名解析, 以数字形式显示源/目地址及端口号
- `-t`, 显示 TCP 相关 socket 信息

参数可以合写为 `netstat -ant`. 命令会产生以下格式的输出信息:
```shell
Proto Recv-Q Send-Q Local Address           Foreign Address         State
```
其中,
- `Recv-Q`, 应用程序尚未取走的输入缓冲区字节数
- `Send-Q`, 通信对方尚未确认的输出缓冲区字节数

**实验步骤**

1.  运行服务器

    此时网络信息为:
    ```shell
    $ netstat -ant | grep 8080
    tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN     
    ```

    此时服务器监听在本地的 `8080` 端口, `0.0.0.0` 表示从任何一个网络接口收到的请求都会被接受. 现在还没有客户端发起连接请求, 所以无法确定客户端地址.

1.  启动 `telnet` 客户端 1

    ```shell
    $ telnet localhost 8080
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    ```

    服务器程序显示:
    ```
    Serving HTTP on port 8080 ...
    Connected by ('127.0.0.1', 52866)
    ```

    此时的网络信息:
    ```shell
    $ netstat -ant | grep 8080
    tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN     
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52866         ESTABLISHED
    tcp        0      0 127.0.0.1:52866         127.0.0.1:8080          ESTABLISHED
    ```
    其中前两行为服务器 `socket` 信息, 最后一行为客户端 `socket` 信息. 可以看到当连接建立后, 系统会创建一个新的连接端点表示已建立的连接, 它具有完整的客户端/服务端信息. 同时处于监听状态的连接仍然存在.

1.  启动 `telnet` 客户端 2, 3

    启动客户端 2, 3 后服务器并没有新的输出, 这在意料之内, 因为示例服务器一次只能服务一个请求. 但是两个客户端都显示正常, 说明连接已经建立.

    查看此时的网络信息:
    ```shell
    $ netstat -ant | grep 8080
    tcp        2      0 0.0.0.0:8080            0.0.0.0:*               LISTEN     
    tcp        0      0 127.0.0.1:52870         127.0.0.1:8080          ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52870         ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52866         ESTABLISHED
    tcp        0      0 127.0.0.1:52868         127.0.0.1:8080          ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52868         ESTABLISHED
    tcp        0      0 127.0.0.1:52866         127.0.0.1:8080          ESTABLISHED
    ```
    可以看到, 现在已经有了三对正常建立的连接. 其中一个由服务器取走进行服务, 余下两个则响应地保存在 `backlog` 队列中. 还能注意到的一个变化是, 监听端口的 `Recv-Q` 值为 2, 等于正在排队的全连接数.

    奇怪的地方来了, 在程序中设置的 `backlog` 值明明是 1, 可现在却如何接受了两个连接? 这个差异由系统实现所致. 其中一类与 `backlog` 对应, 我们遇到的另一类的实现方式为 `3 * backlog / 2 + 1`. 所以队列中最多能有两个连接.

    如果这时再开一个客户端, 可以预见连接是不能正常建立的.

1.  启动客户端 4

    客户端的请求得不到响应, 一段时间后进入超时状态.
    ```shell
    $ telnet localhost 8080
    Trying 127.0.0.1...
    telnet: Unable to connect to remote host: Connection timed out
    ```

    在连接过程中, 服务端系统不响应客户端的 `SYN` 数据包, 使连接无法建立.
    ```shell
    $ netstat -ant | grep 8080
    tcp        2      0 0.0.0.0:8080            0.0.0.0:*               LISTEN     
    tcp        0      0 127.0.0.1:52870         127.0.0.1:8080          ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52870         ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52866         ESTABLISHED
    tcp        0      1 127.0.0.1:52888         127.0.0.1:8080          SYN_SENT   
    tcp        0      0 127.0.0.1:52868         127.0.0.1:8080          ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52868         ESTABLISHED
    tcp        0      0 127.0.0.1:52866         127.0.0.1:8080          ESTABLISHED
    ```

1.  客户端服务器通信

    现在, 有 1, 2, 3, 共三个客户端与服务器建立起了连接. 在客户端看来连接一切正常, 但是并不代表一定能与服务端正常通信.

    从 2 或 3 两个客户端中选择一个向服务器发送一段数据.
    ```shell
    $ telnet localhost 8080
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    hello!
    ```
    服务器未作任何响应. 查看网络信息
    ```shell
    $ netstat -ant | grep 8080
    tcp        2      0 0.0.0.0:8080            0.0.0.0:*               LISTEN     
    tcp        0      0 127.0.0.1:52870         127.0.0.1:8080          ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52870         ESTABLISHED
    tcp        0      0 127.0.0.1:8080          127.0.0.1:52866         ESTABLISHED
    tcp        0      0 127.0.0.1:52868         127.0.0.1:8080          ESTABLISHED
    tcp        8      0 127.0.0.1:8080          127.0.0.1:52868         ESTABLISHED
    tcp        0      0 127.0.0.1:52866         127.0.0.1:8080          ESTABLISHED
    ```
    可以看到, 在倒数第二行的 `socket` 信息中, 有 8 字节的输入缓冲区数据未被读取, 正好等于 `hello!\r\n` 的长度. 这也容易解释: 服务器当前正在与客户端 1 通信, 只有处理完 1 的请求, 才会去服务后续客户端.

### 小结
经过以上原理的学习和实际的检验, 我们就为了弄清楚 `backlog` 这一参数的含义. 现在应该已经有了一个基本认识, 简单来说就是服务器处理的是已经建立好的连接, 而连接由操作系统管理, 通过系统接口我们可以调整系统的管理行为, 如果服务器处理不过来, 系统会将连接放入长度为 `min(backlog, somaxconn)` 的队列中管理.

## 参考资料
- [What is the difference between a port and a socket?](https://stackoverflow.com/a/152863)
- [Essentials of Python Socket Programming You Should Know](http://www.techbeamers.com/python-tutorial-essentials-of-python-socket-programming/)
- [Python socket – network programming tutorial](https://www.binarytides.com/python-socket-programming-tutorial/)
- [IPv4 variable reference](https://www.frozentux.net/ipsysctl-tutorial/chunkyhtml/tcpvariables.html)
- [netstat(8) - Linux man page](https://linux.die.net/man/8/netstat)
