# socket 基础
- 通过 `socket` 模块可以直接访问操作系统提供的 BSD socket 接口.
- socket 是连接的一个端点, 包含 IP 地址和端口号.
- 一个 TCP 连接有两个端点, 所以一个 socket 不能代表连接, 必须同时得到处于连接两端的一对 socket. 也就是说连接至少包含四项信息:
  ```
  (client IP, client port, server IP, server port)
  ```
- socket 既可以用于同一台设备中的不同进程间通信, 也可用于不同设备中的进程间通信.

## 创建 socket
- 创建 socket 通常只要提供两个参数:
  ```python
  sock_obj = socket.socket(family, type)
  ```

  其中,
  - `family` 表示使用的地址或协议类型.
    - `AF_NET` 表示使用 IPv4 地址.
  - `type` 表示通信方式.
    - `SOCK_STREAM` 表示使用 TCP 协议,
    - `SOCK_DGRAM` 表示使用 UDP 协议.

- 创建过程中的异常通过 `socket.error` 捕获.

## 客户端
- 客户端程序的一般操作为:
  1. 创建 socket;
  1. 初始化连接;
  1. 收发数据;
  1. 关闭连接.
- 示例
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
- 服务端程序的一般操作为:
  1. 创建 socket;
  1. 绑定至一个地址;
  1. 等待连接请求;
  1. 接受请求, 建立连接;
  1. 收发数据;
  1. 关闭连接.
- 示例
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
- 使用 `listen()` 开始等待连接请求, 参数表示等待连接的队列长度.
- `accept()` 接受连接, 返回一个新的 socket 表示完整的连接, 和客户端地址.
- 服务端 socket 的接收缓冲区同样是有限的, 如果服务端处理地比较慢, 发送数据的客户端会进入阻塞状态.

## 参考资料
- [What is the difference between a port and a socket?](https://stackoverflow.com/a/152863)
- [Essentials of Python Socket Programming You Should Know](http://www.techbeamers.com/python-tutorial-essentials-of-python-socket-programming/)
- [Python socket – network programming tutorial](https://www.binarytides.com/python-socket-programming-tutorial/)
