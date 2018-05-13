# Namespace 实验
下面的一些操作(主要是挂载文件系统), 可能会修改掉系统文件, 所以保险一些的话可以在虚拟机中运行. 在 `Docker` 容器中, 像修改主机名的一些操作是无法执行的.
## 程序框架
后续操作都在这段程序的基础上修改运行.
```c
#define _GNU_SOURCE
#include <sys/wait.h>
#include <sched.h>
#include <unistd.h>
#include <stdio.h>

#define STACK_SIZE (1024 * 1024)
static char stack[STACK_SIZE];
static char* const child_args[] = {
  "/bin/bash", NULL
};

static int child(void *arg) {
  printf("Enter child: \n");
  execv("/bin/bash", child_args);
  return 0;
}

int main(int argc, char *argv[]) {
  printf("Enter main: \n");
  pid_t pid = clone(child, stack + STACK_SIZE, SIGCHLD, NULL);
  waitpid(pid, NULL, 0);
  printf("Exit main.\n");
  return 0;
}
```
其中,
- `execv` 第一个参数为可执行文件的路径; 第二个参数为传给可执行文件的运行参数数组, 要以 `NULL` 指针结束. 这行语句的作用是使用 `bash` 打开一层新的 `bash`.
- `clone` 开启一个新的进程. 第一个参数为子进程执行的方法; 第二个参数为子进程栈空间的地址, 该空间由调用(父)进程分配, 在程序中为 `stack` 数组所在空间, 又因为栈空间从高地址向低地址增长, 所以程序中用 `stack + STACK_SIZE` 指向了地址的最高位; 第三个参数设置子进程结束后返回给调用进程的信号, 还有子进程与调用进程间共享的资源; 最后一个参数为传给子进程的参数.
- `waitpid` 暂停调用进程, 等待子进程结束.

在实验中通过 `clone` 开启新的 `bash` 进程, 并在第三个参数中设置不同的 `namespace` 选项, 观察效果.

## UTS namespace
> UTS (UNIX Time-sharing System) namespace 提供了主机名和域名的隔离.

修改 `clone` 调用.
```c
  pid_t pid = clone(child, stack + STACK_SIZE, SIGCHLD | CLONE_NEWUTS, NULL);
```

编译并执行.
```
$ gcc -Wall ns_example.c && ./a.out
```

程序运行后会进入新开启的 `bash`, 在其中修改主机名.
```
$ sudo hostname container
```

查看主机名, 可以看到已经变成了 `container`.
```
$ hostname
container
```

但是打开一个新的 `bash` 查看主机名并未发生变化, 说明修改只发生在命名空间内.

在此基础上修改程序, 使程序每次运行都修改主机名为 `container`. 修改后需要使用 `sudo` 执行程序.
```c
// 省略...
#include <string.h>

// 省略...
static int child(void *args) {
  printf("Enter child. \n");
  char hostname[] = "container";
  sethostname(hostname, strlen(hostname));
  execv("/bin/bash", child_args);
  return 0;
}

int main(int argc, char *argv[]) {
  printf("Enter main. \n");
  pid_t pid = clone(child, stack + STACK_SIZE, CLONE_NEWUTS | SIGCHLD, NULL);
  // 省略...
}
```

## IPC namespace
> IPC (Inter-Process Communication) namespace 涉及到信号量, 消息队列和共享内存等资源.

修改 `clone` 调用.
```c
  pid_t pid = clone(child, stack + STACK_SIZE,
    CLONE_NEWUTS | CLONE_NEWIPC | SIGCHLD, NULL);
```

编译运行后, 使用 `ipcmk` 命令新建消息队列.
```
$ gcc -Wall ns_example.c && sudo ./a.out
Enter main.
Enter child.
root@container:~/ns# ipcmk -Q
Message queue id: 0
```

使用 `ipcs` 查看消息队列.
```
root@container:~/ns# ipcs -q

------ Message Queues --------
key        msqid      owner      perms      used-bytes   messages    
0xa27ae9a8 0          root       644        0            0           
```

退出子进程后再次查看, 是没有子进程做出的修改的.
```
$ ipcs -q

------ Message Queues --------
key        msqid      owner      perms      used-bytes   messages    
```

## PID namespace
> PID (Process ID) namespace 隔离进程号, 使不同命名空间下的进程可以有相同的进程号.

修改 `clone` 调用.
```c
pid_t pid = clone(child, stack + STACK_SIZE, CLONE_NEWUTS | CLONE_NEWPID |
  SIGCHLD, NULL);
```

编译运行, 进入子进程, 使用 `echo $$` 查看当前进程 `ID`.
```
$ gcc -Wall ns_example.c && sudo ./a.out
Enter main.
Enter child.
root@container:~/ns# echo $$
1
```

可以看到进程 `ID` 为 1, 说明创建了子进程空间, 并且是该空间内的第一个进程.

## Mount namespace
> Mount namespace 隔离文件系统挂载点. 它是第一个 Linux 命名空间.

**这里遇到问题, 按照下面的步骤在子程序中重新挂载 `/proc` 后会影响到主机文件系统.**

修改 `clone` 调用.
```c
  pid_t pid = clone(child, stack + STACK_SIZE, CLONE_NEWPID | CLONE_NEWNS |
    CLONE_NEWUTS | SIGCHLD, NULL);
```

编译运行, 重新挂载 `/proc`, 查看所有进程.
```
$ gcc -Wall ns_example.c && sudo ./a.out
root@container:~/ns# mount -t proc none /proc
root@container:~/ns# ps ax
  PID TTY      STAT   TIME COMMAND
    1 tty1     S      0:00 /bin/bash
   12 tty1     R+     0:00 ps a
```

在退出后再次查看仍会提示错误.
```
root@container:~/ns# exit
exit
Exit main.
$ ps ax
Error, do this: mount -t proc proc /proc
```

## Network namespace
> Network namespace 会对网络相关的系统资源进行隔离.

修改 `clone` 调用.
```c
  pid_t pid = clone(child, stack + STACK_SIZE, CLONE_NEWNET | CLONE_NEWUTS |
    SIGCHLD, NULL);
```

分别在执行前和执行后, 使用 `ip link` 查看网络设备.
```
root@container:~/ns# ip link
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
```
进入子程序后, 只列出了一个回环设备, 而且状态为 `DOWN`, 因此要使容器能够连接到网络仍有许多工作要做.

## 总结
最后还有一个 `user namespace` 用于隔离用户和用户组, 这部分的实验就略过了.

通过前面几个命名空间的操作, 也大概了解了用于隔离的系统调用的使用方法, 知道了在资源隔离中都要考虑哪些方面的内容.

### Cheet sheet
```
#  文件编译
gcc -Wall <file> [-o output]

# 当前 Shell 进程 ID
echo $$

# 前一个命令的退出状态码
echo $?

# 退出当前 Shell
exit

# vi 撤销与恢复
u
ctrl + r

# 查看修改主机名
hostname
hostname <new_name>

# 创建, 查看, 删除消息队列
ipcmk -Q
ipcs -q
ipcrm -q <id>
ipcrm -Q <key>

# 显示所有进程
ps ax

# mount 将 device 中 type 类型的文件系统挂载到 dir
mount [-t type] <device> <dir>

# 显示网络设备
ip link
```

## 参考阅读
- Docker 进阶与实战 2.4.2
- Docker 容器与容器云 3.1.1
- [Separation Anxiety: A Tutorial for Isolating Your System with Linux Namespaces](https://www.toptal.com/linux/separation-anxiety-isolating-your-system-with-linux-namespaces)
