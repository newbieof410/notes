# Build Git Server with Docker

## 直接在 Ubuntu 上部署
在使用 `Docker` 前, 先搞清楚如何直接部署在服务器上.

### 添加 git 用户
首先新建一个用户, 专用做仓库管理, 这里起名为 `git`.
- 添加用户
  ```
  $ sudo adduser git
  ```

- 切换为用户 git
  ```
  $ su git
  ```

### 新建公钥管理目录
使用 `SSH` 作为连接和认证远程服务器的方式, 需要保存连接者的 `SSH` 公钥.

- 进入用户目录.
  ```
  $ cd
  ```

- 新建 `.ssh` 目录, 修改权限为只有 `git` 用户可以操作(`rwx`)该目录.
  ```
  $ mkdir .ssh && chmod 700 .ssh
  ```

- 新建文件, 用于保存已认证用户的公钥, 权限为 git 可读写.
  ```
  $ touch .ssh/authorized_keys && chmod 600 .ssh/authorized_keys
  ```

- 添加使用者公钥. 这条命令会把公钥添加到 `authorized_keys` 末尾.
  ```
  $ cat <id_rsa.pub> >> ~/.ssh/authorized_keys
  ```

#### 生成 SSH Key
在使用 `SSH` 连接前, 需要生成用于认证的 Key.
- 生成 Key.
  ```
  ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
  ```
  - `-t` 指定 key 的类型.
  - `-b` 指定 key 的长度.
  - `-C` 设置 comment.

生成 Key 后, 可以选择使用 `ssh-agent` 对私钥进行管理.
- 启动 `ssh-agent`. `eval` 是 `Linux` 的内置命令, 会把后面的参数当作 `shell` 命令执行.
  ```
  eval "$(ssh-agent -s)"
  ```
- 添加到 `ssh-agent`.
  ```
  ssh-add <id_rsa>
  ```

#### 解锁 root 用户
修改 `.ssh` 文件权限后, 使用本机的其他用户身份 (非 `git` 用户) 无法进入这个文件夹, 在添加公钥时, 需要使用 `root` 用户权限.

- `root` 用户具有系统最高权限, 默认处于锁定状态. 解锁方法:
  ```
  $ sudo passwd root
  ```
- 按照提示输入密码即可创建成功. 切换到 `root` 用户.
  ```
  $ su
  ```
- 操作完成后, 换回普通用户.
  ```
  # su <username>
  ```

### 测试连接状态
- 命令用法 `ssh [user@]hostname`. 以 `git` 用户的身份连接到本机的命令为:
  ```
  ssh git@localhost
  ```

- 连接成功会进入 `shell`. 可以看到用户名变成了 `git`.
  ```
  $ ssh git@localhost
  Welcome to Ubuntu 18.04 LTS (GNU/Linux 4.15.0-20-generic x86_64)

    ...

  Last login: Wed May 16 15:36:08 2018 from 127.0.0.1
  git@tom-laptop:~$
  ```

#### 问题处理
测试过程中遇到问题:
```
ssh: connect to host localhost port 22: Connection refused
```
- 使用 `ufw` 开放端口 `22`. 这是 `SSH` 使用的 well-known port number.
  ```
  sudo ufw allow 22
  ```

- 检查 `sshd` 是否安装. 如果已经安装, 命令会输出安装位置.
  ```
  $ which sshd
  /usr/sbin/sshd
  ```

- 如果上一步没有输出, 需要安装 `sshd`.
  ```
  $ sudo apt install openssh-server
  ```

### 限制 git 用户
连接成功后, 已登录的用户可以使用 `shell` 在服务器执行 `git` 用户权限下的各种操作. 为了保证服务器的安全, 需要限制 `git` 用户登陆后使用 `git-shell`, 在该 `shell` 中只能使用 `Git` 操作.

- `/etc/shells` 中记录着登陆后可以使用的 `shell`. 要保证其中记录着 `git-shell` 的信息.
  ```
  $ cat /etc/shells
  ```
- 如果没有, 检查 `git-shell` 是否已安装, 并找到其安装位置.
  ```
  $ which git-shell
  ```
- 将上一步得到的路径添加到 `/etc/shells`.
  ```
  $ sudo vim /etc/shells
  ```
- 使用命令 `chsh <username> -s <shell>` 更改用户登录后使用的 `shell`. 设置 `git` 用户登录后使用 `git-shell`.
  ```
  $ sudo chsh git -s $(which git-shell)
  ```
- 设置成功后, `git` 用户就只能执行 `push` 和 `pull` 等操作, 而不能登录到服务器的 `shell` 中.
  ```
  $ ssh git@localhost
  Welcome to Ubuntu 18.04 LTS (GNU/Linux 4.15.0-20-generic x86_64)

    ...

  fatal: Interactive git shell is not enabled.
  hint: ~/git-shell-commands should exist and have read and execute access.
  Connection to localhost closed.
  ```
- 在 `/etc/passwd` 文件中也可以看到更改
  ```
  git:x:1001:1001:,,,:/home/git:/usr/bin/git-shell
  ```

### 创建仓库
在用户可以使用 `Git` 操作前, 需要在 `Git` 服务器上先创建一个仓库. 每个项目都要单独建一个.

- 选一个位置, 仓库命名以 `.git` 作为后缀.
  ```
  mkdir -p repo/project.git
  ```
- 进入仓库文件夹, 使用 `--bare` 选项, 初始化一个没有工作区的 `Git` 仓库.
  ```
  $ cd project.git
  $ git init --bare
  Initialized empty Git repository in /home/git/repo/project.git/
  ```
- 修改仓库的所有者为 `git`.
  ```
  $ sudo chown -R git:git project.git
  ```

初始化成功后, 用户就可以像使用 `GitHub` 一样使用这个本地的远程仓库了.
- 提交修改. 添加远程仓库时, 需要将 `hostname` 改为 `Git` 服务器的 `IP` 地址, 或者主机名, 如果设置了 `DNS` 的话. 仓库的位置要和初始化位置一致.
  ```
  $ git remote add origin git@hostname:/home/git/repo/project.git
  $ git push origin master
  ```
- 仓库克隆.
  ```
  $ git remote add origin git@gitserver:/srv/git/project.git
  $ git push origin master
  ```

## 小结
虽然在部署时有许多细节需要考虑, 但在总体上只有下面几步:
1. 新建用于管理仓库的用户;
1. 修改登录 `Shell`, 提高安全性;
1. 启动 `SSH` 服务, 添加授权使用者的公钥;
1. 初始化一个仓库.

## 参考文档
- [Git on the Server - Setting Up the Server](https://git-scm.com/book/en/v2/Git-on-the-Server-Setting-Up-the-Server)
- [搭建 Git 服务器](https://www.liaoxuefeng.com/wiki/0013739516305929606dd18361248578c67b8067c8c017b000/00137583770360579bc4b458f044ce7afed3df579123eca000)
- [Connecting to GitHub with SSH](https://help.github.com/articles/connecting-to-github-with-ssh/)
- [An Introduction to Uncomplicated Firewall (UFW)](https://www.linux.com/learn/introduction-uncomplicated-firewall-ufw)
- [connect to host localhost port 22: Connection refused](https://stackoverflow.com/a/17335975)
- [How to Become Root in Linux](https://www.wikihow.com/Become-Root-in-Linux)
