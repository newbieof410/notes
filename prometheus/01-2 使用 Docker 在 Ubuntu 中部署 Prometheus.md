# 使用 Docker 在 Ubuntu 中部署 Prometheus
在上一部分中, 使用了 `node_exporter` 容器的 `IP` 地址对 `Prometheus` 作了配置. 这样虽然可以连接成功, 但是容器的地址是动态分配的, 如果重启后地址发生了变化, 之前的配置也就没了作用. 下面就使用一种新的方法连接容器.

## 使用 `--link` 选项
重新运行一个 `node_exporter` 容器, 使用 `--name` 自定义名称, 这里没有使用 `-p` 映射容器端口.
```
$ docker run -d --name node prom/node-exporter
```

重新运行 `Prometheus`.
```
$ docker run -d -p 9090:9090 --link node:node1 --name prom prom/prometheus
```
可以看到, 在上面的命令中使用了 `--link` 选项. 它接收用冒号 (`:`) 分隔的两个参数, 前面的 `node` 是要连接的容器名称, 也就是刚刚启动的 `node_exporter`, 后面的 `node1` 是它的别名, 在 `prom` 内部使用.

接下来, 还是需要修改 `Prometheus` 的配置文件.
```
$ docker exec -it prom vi /etc/prometheus/prometheus.yml
```

添加抓取目标.
```yml
- job_name: 'node_exporter'            
  static_configs:                      
    - targets: ['node1:9100']
```
这里就把 `node_exporter` 的固定地址改为了运行它的容器的别名, 使用时会被自动转换为对应的 `IP` 地址.

重启后 `$ docker restart prom`, 进入 [http://localhost:9090/targets](http://localhost:9090/targets) 页面查看修改效果.

## 使用 `-v` 选项
容器有自己的独立文件系统, 每次对配置文件的修改都需要进入容器操作, 而且删除容器后, 相应的配置文件也会丢失. 不过, `Docker` 提供了 `volume` 机制, 可以帮助我们把主机里的文件绑定到容器中, 实现主机与容器间的数据共享. 这样就能在容器外编辑保存配置文件了.

先从 `prom` 中把配置文件复制出来.
```
docker exec -it prom vi /etc/prometheus/prometheus.yml
```
下面删除了部分注释信息. 在当前目录下保存为 `prometheus.yml`
```yml
# my global config
global:                                                         
  scrape_interval:     15s
  evaluation_interval: 15s

# Alertmanager configuration
alerting:                   
  alertmanagers:                          
  - static_configs:                         
    - targets:                      
      # - alertmanager:9093

# Load rules once and periodically evaluate them according to the global 'evaluation_interval'.
rule_files:             
  # - "first_rules.yml"      
  # - "second_rules.yml"   

scrape_configs:
  - job_name: 'prometheus'
    static_configs:            
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node1:9100']
```

关闭并删除容器 `prom`.
```
$ docker container rm -f prom
```

重新运行一个 `Prometheus` 容器.
```
$ docker run -d -p 9090:9090 -v $PWD/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
> --link node:node1 --name prom prom/prometheus
```
这里将当前目录下的配置文件 `$PWD/prometheus.yml` 挂载到了容器的 `/etc/prometheus/prometheus.yml` 目录下, 并且使用只读 `ro` 选项.

## 总结
在这部分内容中, 分别使用了 `--link` 实现容器间的连接, 使用 `-v` 挂载主机中的文件到容器中.

配置过程中如果 [http://localhost:9090/targets](http://localhost:9090/targets) 无法访问, 可以使用 `docker container ls` 检查容器是否正常运行, 使用 `docker logs [容器名]` 查看日志信息.
