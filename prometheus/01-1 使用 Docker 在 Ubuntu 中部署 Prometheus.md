# 使用 Docker 在 Ubuntu 中部署 Prometheus

## 运行 Prometheus
```
docker run -d -p 9090:9090 prom/prometheus
```
- `-d` 在后台运行容器, 并显示出容器 ID
- `-p 9090:9090` 把主机的 9090 端口映射到容器的 `9090` 端口

容器启动后, 使用 `docker container ls` 命令即可查看到正在运行的 `Prometheus` 容器.
```
$ docker container ls
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
6de7210beda7        prom/prometheus     "/bin/prometheus --c…"   7 minutes ago       Up 7 minutes        0.0.0.0:9090->9090/tcp   musing_liskov
```

`Prometheus` 提供了网页控制台, 可以从这里进入 [http://localhost:9090/graph](http://localhost:9090/graph). 在页面中选择 `Status-->Targets`, 可以看到它默认只配置了对自身运行状态的监测.

## 运行 node_exporter
**注意** `node_exporter` 用于收集宿主机的运行数据, 但是这里我们把它运行在容器中, 在默认情况下收集的数据只能反映容器的运行状况.

```
docker run -d -p 9100:9100 prom/node-exporter
```
通过 [http://localhost:9100/metrics](http://localhost:9100/metrics) 可以查看到它收集到的信息.

## 配置 Prometheus
将新启动的 `node-exporter` 作为 `Prometheus` 的数据抓取对象. 默认情况下, 容器中的 `Prometheus` 配置文件位于 `/etc/prometheus/prometheus.yml`, 现在进入容器修改这个文件.

```
docker exec -it musing_liskov vi /etc/prometheus/prometheus.yml
```
- `exec` 在运行中的容器中执行命令
- `-it` 使容器可以接受输入并分配一个虚拟控制台
- `musing_liskov` 运行 `Prometheus` 容器的名称. 因为使用 `run` 命令时没有自定义名称, 这里的名称由 `Docker` 随机产生. 另外, 此处也可以用容器 ID 代替.
- `vi` 使用 `vi` 打开配置文件

在默认配置文件中, `Prometheus` 对自身抓取的配置为
```yml
scrape_configs:                                                
  # The job name is added as a label `job=<job_name>` to any timeseries scraped
  # from this config.
  - job_name:
    'prometheus'                                                                
    # metrics_path defaults to'/metrics'                               
    # scheme defaults to 'http'.             
    static_configs:                                                           
      - targets: ['localhost:9090']  
```

按照这个格式, 将 `node-exporter` 添加为抓取对象. 但是还需要知道它的 `IP` 地址, 使用下面的命令查看
```
$ docker inspect reverent_bassi
...
            "Networks": {
                "bridge": {
                    ...
                    "Gateway": "172.17.0.1",
                    "IPAddress": "172.17.0.3",
                    ...
                }
            }
```
其中, `inspect` 后面接的是 `node-exporter` 容器的名称. 重新回到配置文件中, 在最后增加
```yml
- job_name: 'node'                     
  static_configs:                      
    - targets: ['172.17.0.3:9100']
```
保存退出. 要让更改生效, 还需要重启 `Prometheus`. 输入命令
```
$ docker restart musing_liskov
```
重启后, 再次进入 [http://localhost:9090/targets](http://localhost:9090/targets) 页面, 可以看到新增加了 `node` 抓取对象, 说明配置成功.

## Cheet Sheet
```shell
# 运行一个新的容器
docker run -d -p <host-port>:<container-port> <image>

# 显示运行中的容器
docker container ls

# 在运行的容器中执行命令
docker exec -it <container> <cmd> [args]

# 显示容器的详细信息
docker inspect <container>

# 重启容器
docker restart <container>
```
