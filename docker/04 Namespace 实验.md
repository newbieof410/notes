# Namespace 实验

## 程序框架
后续操作都在下面这段程序的基础上修改执行. 在程序中使用 `clone` 系统调用创建一个子进程, 并将子进程放入新的命名空间.

`clone` 的使用方式为:
```c
int clone(int (*fn)(void *), void *child_stack,
          int flags, void *arg);
```

`clone` 的作用类似于 `fork`, 都用于创建子进程. 不同的是 `clone` 创建的子进程可以共享父进程的部分上下文, 比如内存空间. 所以 `clone` 可以用来实现多线程. 另一个不同点是, `clone` 创建的子进程会从 `fn` 所指向的函数位置开始执行, 参数通过 `arg` 传入.

父进程要负责为子进程提供栈空间. 在 Linux 系统中, 栈地址由高向低增长, 所以 `child_stack` 通常指向子进程栈空间的最高地址处, 即栈底.

`clone` 创建的子进程与父进程共享哪些资源使用 `flags` 参数控制. 实验中就是通过设置这个参数, 来将子进程放入不同的命名空间. 同时, `flags` 还关系到在子进程结束后, 父进程会收到的信号.

```c
#define _GNU_SOURCE
#include <errno.h>
#include <sys/wait.h>
#include <sched.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define STACK_SIZE (1024 * 1024)

void unix_error(char *msg) {
    fprintf(stderr, "%s: %s\n", msg, strerror(errno));
    exit(0);
}

char * const child_args[] = {
    "/bin/bash", NULL
};

int child(void *args) {
    printf("Enter child.\n");

    /*Open a new bash shell*/

    if (execv(child_args[0], child_args) < 0)
        unix_error("Execv error");

    exit(0);
}

int main(int argc, char *argv[]) {
    char *stack;
    char *stackTop;
    pid_t pid;

    printf("Enter main.\n");

    /*Allocate stack for child*/

    stack = malloc(STACK_SIZE);
    if (stack == NULL)
        unix_error("Malloc error");
    stackTop = stack + STACK_SIZE;

    /*Create child*/

    pid = clone(child, stackTop, SIGCHLD, NULL);
    if (pid < 0)
        unix_error("Clone error");

    /*Wait for child*/

    if (waitpid(pid, NULL, 0) < 0)
        unix_error("Waitpid error");

    printf("Exit main.\n");

    exit(0);
}
```

这里还有两个函数要说明.

`execv` 用于在当前的进程上下文中开启一个新的进程. 新进程会取代旧进程. 其第一个参数 `path` 为要执行的文件的路径; 第二个参数 `argv` 为传给新进程的参数数组, 要以 `NULL` 指针结束. 按照惯例, 数组的第一个元素应该是要执行的文件名.

在子进程中, 使用该函数打开一个新的 `bash` 以观察命名空间的变化.

`waitpid` 用于暂停父进程, 等待子进程状态的变化.

## UTS Namespace
> UTS (UNIX Time-sharing System) namespace 提供了主机名和域名的隔离.

修改 `clone` 调用.
```c
    pid = clone(child, stackTop, CLONE_NEWUTS | SIGCHLD, NULL);
```

编译并执行.
```
$ gcc -Wall ns_example.c && sudo ./a.out
```

程序运行后会进入新开启的 `bash`, 在其中修改主机名.
```
# hostname container
```

查看主机名, 可以看到已经变成了 `container`.
```
# hostname
container
```

但是 `exit` 退出子进程后再次查看, 主机名并未发生变化. 说明修改只发生在子进程命名空间内.

在此基础上修改程序, 使程序每次运行都修改主机名为 `container`.
```c
int child(void *args) {
    printf("Enter child.\n");

    char hostname[] = "container";
    if (sethostname(hostname, strlen(hostname)) < 0)
        unix_error("Sethostname error");

    // ...
}
```

## IPC Namespace
> IPC (Inter-Process Communication) namespace 涉及到信号量, 消息队列和共享内存等资源.

修改 `clone` 调用.
```c
    pid = clone(child, stackTop, CLONE_NEWIPC | CLONE_NEWUTS | SIGCHLD, NULL);
```

编译运行后, 使用 `ipcmk` 命令新建消息队列.
```
root@container:~/ns# ipcmk -Q
Message queue id: 0
```

使用 `ipcs` 可以查看到刚刚创建的 id 为 0 的消息队列.
```
root@container:~/ns# ipcs -q

------ Message Queues --------
key        msqid      owner      perms      used-bytes   messages    
0xa27ae9a8 0          root       644        0            0           
```

退出子进程后再次查看, 没有显示出该队列.
```
$ ipcs -q

------ Message Queues --------
key        msqid      owner      perms      used-bytes   messages    
```

## PID Namespace
> PID (Process ID) namespace 隔离进程号, 使不同命名空间下的进程可以有相同的进程号.

修改 `clone` 调用.
```c
    pid = clone(child, stackTop, CLONE_NEWPID |  CLONE_NEWIPC | CLONE_NEWUTS | SIGCHLD, NULL);
```

编译运行, 进入子进程. 使用 `echo $$` 查看当前进程 id 和父进程 id.
```
root@container:~/ns# echo $$
1
root@container:~/ns# echo $PPID
0
```

可以看到进程 id 为 1, 没有父进程. 说明子进程感知不到外部进程.

## Mount Namespace
> Mount namespace 隔离文件系统挂载点. 它是第一个 Linux 命名空间.

Mount Namespace 用于隔离容器中进程与主机的文件系统. 但要注意的是, 这里的隔离发生在挂载操作之后. 也就是说, 即使我们创建了一个进程, 并把它放在了一个隔离的 Mount Namespace, 在重新挂载文件系统之前, 它看到的仍是主机的文件系统.

因为 `ps` 命令获取的信息来自于 `/proc` 文件, 如果在容器中没有重新挂载 `/proc`, 那么在容器中执行 `ps` 命令仍会看到整个主机的进程信息.

在这个实验中, 可以观察一下 `ps` 命令在 `/proc` 重新挂载前和挂载后的输出信息.

在 `clone` 中添加 `CLONE_NEWNS`.
```c
  pid_t pid = clone(child, stack + STACK_SIZE, CLONE_NEWPID | CLONE_NEWNS |
    CLONE_NEWUTS | SIGCHLD, NULL);
```

编译运行. 先简单查看进程数, 然后重新挂载 `/proc`, 再次查看, 此时只显示出命名空间中的两个进程.
```
$ gcc -Wall ns_example.c && sudo ./a.out
root@container:~/ns# ps ax | wc -l
297
root@container:~/ns# mount -t proc proc /proc
root@container:~/ns# ps ax
  PID TTY      STAT   TIME COMMAND
    1 tty1     S      0:00 /bin/bash
   12 tty1     R+     0:00 ps a
```

从子进程退出后可能会遇到下面的错误, 这时只要以 root 身份执行提示中的命令就可以了.
```
root@container:~/ns# exit
exit
Exit main.
$ ps ax
Error, do this: mount -t proc proc /proc
```

这个问题是 Linux 的共享挂载机制造成的. 如果主挂载点被设置为共享的挂载方式, 那么在子进程中的子挂载点也会默认为共享状态. 在共享状态下, 一端的修改会传递到另外一端, 所以在命名空间中的修改才会影响到主机文件系统.

要解决这个问题, 只要在重新 `mount` 前, 将挂载点设置为私有挂载就可以了.
```
mount --make-private /proc
```

## Network Namespace
> Network namespace 会对网络相关的系统资源进行隔离.

修改 `clone` 调用.
```c
    pid = clone(child, stackTop, CLONE_NEWNET | CLONE_NEWNS |
                CLONE_NEWPID |  CLONE_NEWIPC | CLONE_NEWUTS | SIGCHLD, NULL);
```

分别在执行前和执行后, 使用 `ip link` 查看网络设备.
```
root@container:~/ns# ip link
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
```
子进程只拥有一个默认的回环设备, 而且状态为 `DOWN`, 所以此时是无法与外界通信的. 要实现与其他命名空间, 以及外界的通信, 需要使用虚拟以太网设备 `veth`.

`veth` 设备一般成对创建, 像网线的两端将两个网络命名空间连接起来. `veth pair` 的创建方式为:

```
$ sudo ip link add veth0 type veth peer name veth1
```

上面的命令创建了两个彼此相连的 `veth` 设备 `veth0` 和 `veth1`. 接下来要将其中一端分配给子进程所在的网络命名空间.

这一步需要打开两个终端窗口. 一个运行子进程, 另一个是默认终端, 在子进程命名空间之外.

为了将 `veth1` 加入子进程命名空间, 需要得到父进程所观察到的子进程 id. 执行以下步骤:
1.  查看父进程 id

    ```
    $ ps aux | grep a.out
    root     28866  0.0  0.0  67600  4340 pts/1    S    11:38   0:00 sudo ./a.out
    root     28877  0.0  0.0   5536   720 pts/1    S    11:38   0:00 ./a.out
    ```
1.  查找子进程 id

    ```
    $ pstree -p 28866
    sudo(28866)───a.out(28877)───bash(28878)
    ```

这里可以看出, 虽然运行在新命名空间中的子进程感知不到父进程, 但是父进程却可以看到子进程.

将 `veth1` 加入子进程.
```
$ sudo ip link set veth1 netns 28878
```

在子进程中查看新加入的网络设备.
```
# ip link
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
10: veth1@if11: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
    link/ether 72:2a:7c:da:55:33 brd ff:ff:ff:ff:ff:ff link-netnsid 0
```

这里的 `veth1@if11` 表示位于连接另一端的网络设备序号为 11.

在 `veth1` 被传入子进程的过程中, 父子进程通过 `pipe` 连接通信.

连接了容器命名空间与全局命名空间后, 还要在主机中处理容器数据包的转发与地址转换, 这即是 `docker0` 所要负责的工作.

## Cheet Sheet
```shell
#  文件编译
gcc -Wall <file> [-o output]

# 当前 Shell 进程 ID
echo $$
# 父进程 ID
echo $PPID
# 前一个命令的退出状态码
echo $?
# 退出当前 Shell
exit

# vi 撤销与恢复
u
ctrl + r

# 查看修改主机名
uname -a
hostname
hostname <new_name>

# 创建, 查看, 删除消息队列
ipcmk -Q
ipcs -q
ipcrm -q <id>
ipcrm -Q <key>

# 显示所有进程
ps aux
# 显示进程树
pstree -p <pid>

# mount 将 device 中 type 类型的文件系统挂载到 dir
mount [-t type] <device> <dir>

# 显示网络设备
ip link
# 创建 veth pair
ip link add <p1-name> type veth peer name <p2-name>
# 将网络设备加入新的网络命名空间
ip link set <p2-name> netns <p2-namespace>
```

## 参考阅读
- Docker 进阶与实战 2.4.2
- Docker 容器与容器云 3.1.1
- [Separation Anxiety: A Tutorial for Isolating Your System with Linux Namespaces](https://www.toptal.com/linux/separation-anxiety-isolating-your-system-with-linux-namespaces)
- [clone(2) - Linux man page](https://linux.die.net/man/2/clone)
- [execve(2) - Linux man page](https://linux.die.net/man/2/execve)
- [waitpid(2) - Linux man page](https://linux.die.net/man/2/waitpid)
- [How do I get the parent process ID of a given child process?](https://askubuntu.com/q/153976)
- [veth - Virtual Ethernet Device](http://man7.org/linux/man-pages/man4/veth.4.html)
