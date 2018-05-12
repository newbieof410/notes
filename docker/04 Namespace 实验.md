# Namespace 实验
## 程序框架
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
  pid_t pid;
  pid = clone(child, stack + STACK_SIZE, SIGCHLD, NULL);
  waitpid(pid, NULL, 0);
  printf("Exit main.\n");
  return 0;
}
```
其中,
- `execv` 第一个参数为可执行文件的路径; 第二个参数为传给可执行文件的运行参数数组, 要以 `NULL` 指针结束. 这行语句的作用是使用 `bash` 打开一层新的 `bash`.
- `clone` 开启一个新的进程. 第一个参数为子进程执行的方法; 第二个参数为子进程栈空间的地址, 该空间由调用进程分配, 在程序中为 `stack` 数组, 又因为栈空间从高地址向低地址增长, 所以程序中用 `stack + STACK_SIZE` 指向了地址的最高位; 第三个参数设置子进程结束后返回给调用进程的信号, 还有子进程与调用进程间共享的资源; 最后一个参数为传给子进程的参数.
- `waitpid` 暂停调用进程, 等待子进程结束.

在实验中通过 `clone` 开启新的 `bash` 进程, 并在第三个参数中设置不同的 `namespace` 选项, 观察效果.

## UTS namespace
> UTS (UNIX Time-sharing System) namespace 提供了主机名和域名的隔离.

修改 `clone` 调用.
```c
  pid_t pid = clone(child, stack + STACK_SIZE,
    SIGCHLD | CLONE_NEWUTS, NULL);
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
  pid_t pid = clone(child, stack + STACK_SIZE,
    CLONE_NEWUTS | SIGCHLD, NULL);
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

退出子进程后再次查看.
```
$ ipcs -q

------ Message Queues --------
key        msqid      owner      perms      used-bytes   messages    
```

## PID namespace
> PID (Process ID) namespace 隔离进程号, 使不同命名空间下的进程可以有相同的进程号.

修改 `clone` 调用.
```c
pid_t pid = clone(child, stack + STACK_SIZE,
  CLONE_NEWUTS | CLONE_NEWPID | SIGCHLD, NULL);
```

编译运行, 进入子进程, 使用 `echo $$` 查看进程 `ID`.
```
$ gcc -Wall ns_example.c && sudo ./a.out
Enter main.
Enter child.
root@container:~/ns# echo $$
1
```

可以看到进程 `ID` 为 1, 说明创建了子进程空间, 并且是该空间内的第一个进程.

## Mount namespace


## 参考阅读
- Docker 进阶与实战 2.4.2
- Docker 容器与容器云 3.1.1
