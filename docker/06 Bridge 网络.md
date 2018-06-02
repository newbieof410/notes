# Brideg 网络
`Docker` 在安装后会自动创建三种网络. 查看网络,
```
$ docker network ls
NETWORK ID          NAME                    DRIVER              SCOPE
8c35f1360801        bridge                  bridge              local
8131ec1c28f9        host                    host                local
70e02c21cd39        none                    null                local
```

命令显示了网络相关的四项信息. 其中,
- `DRIVER` 网络使用的驱动;
- `SCOPE` 网络的范围. `local` 说明网络只在本机使用.

这几个预先创建的网络不能被删除.
```
$ docker network rm bridge host none
Error response from daemon: bridge is a pre-defined network and cannot be removed
Error response from daemon: host is a pre-defined network and cannot be removed
Error response from daemon: none is a pre-defined network and cannot be removed
```

除了使用上面三种驱动的网络, `Docker` 还支持 `macvlan` 和 `overlay` 网络驱动.
```
$ docker info
...
Plugins:
 Volume: local
 Network: bridge host macvlan null overlay
...
```

不同的驱动有着各自的适用场景. 其中的 `bridge` 是默认的网络驱动, 它只在本机有效, 通常在本机的多个容器间有通信需求时使用.

`bridge` 驱动使用 `Linux bridge` 创建网络, 查看可以使用 `brctl` 命令.
```
$ sudo apt install bridge-utils

$ brctl show
bridge name	bridge id		STP enabled	interfaces
docker0		8000.0242c154be7b	no		
```

`docker0` 是默认创建的 `bridge` 网络. 会尝试在 `172.16.0.0/16` 地址段尝试创建子网.

查看详细信息.
```
$ ip address show docker0
7: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default
    link/ether 02:42:c1:54:be:7b brd ff:ff:ff:ff:ff:ff
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
       valid_lft forever preferred_lft forever
```

运行新容器时, 如果没有特别指定, 都会连接到默认的 `bridge` 网络, 并在子网内分配 `IP` 地址.

```
$ docker run -d ubuntu sleep infinity
```
这条命令运行起一个 `ubuntu` 容器, 使用 `-d` 选项和 `sleep` 命令使其保持在后台运行.

查看容器地址.
```
$ docker inspect <container>
...
"Gateway": "172.17.0.1",
"GlobalIPv6Address": "",
"GlobalIPv6PrefixLen": 0,
"IPAddress": "172.17.0.2",
...
```

网桥有物理和软件两种实现方式, 但不管如何实现, 它都是一个二层设备, 也就是只要 `MAC` 地址来转发数据帧, 通常也不需要分配 `IP` 地址. 但是从配置中可以看到 `docker0` 还承担着路由 (`Gateway`) 的功能, 所以也有一个地址.

运行 `brctl show` 查看网桥状态.
```
$ brctl show
bridge name	bridge id		STP enabled	interfaces
docker0		8000.0242c154be7b	no		veth2869cfe
```

```
$ ip a
15: veth2869cfe@if14: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master docker0 state UP group default
    link/ether f2:a2:30:18:69:21 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet6 fe80::f0a2:30ff:fe18:6921/64 scope link
       valid_lft forever preferred_lft forever
```

```
$ docker network inspect bridge
...
"Containers": {
    "330e9bc2c104081042b42aec2dbdb14901dde964153c866f046385fa045b6c50": {
        "Name": "wizardly_mcnulty",
        "EndpointID": "137422bed79f7423c74d8045f91ff0ba751bdd923516c2338d3c6569a75943ce",
        "MacAddress": "02:42:ac:11:00:02",
        "IPv4Address": "172.17.0.2/16",
        "IPv6Address": ""
    }
}
...
```

## 参考资料
- [Bridge networking](https://github.com/docker/labs/blob/master/networking/A2-bridge-networking.md)
- [Network drivers](https://docs.docker.com/network/#network-drivers)
- [Use bridge networks](https://docs.docker.com/network/bridge/)
- The Docker Book
- [Why IP address for Linux Bridge which is layer 2 virtual device?](https://unix.stackexchange.com/questions/153281/why-ip-address-for-linux-bridge-which-is-layer-2-virtual-device)
