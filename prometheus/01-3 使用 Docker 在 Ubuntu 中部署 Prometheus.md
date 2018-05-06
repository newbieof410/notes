# 使用 Docker 在 Ubuntu 中部署 Prometheus
`Prometheus` 提供了基本的数据展示功能, 为了有更好的可视化效果, 现在把数据接入 `Grafana` 中显示.

> Grafana is an open source, feature rich metrics dashboard and graph editor for Graphite, Elasticsearch, OpenTSDB, Prometheus and InfluxDB.

## 运行 Grafana
```
$ docker run -d -p 3000:3000 --link prom:prom --name grafana grafana/grafana
```
`Grafana` 需要从 `Prometheus` 中获取数据, 这里还是使用 `--link` 建立与 `Prometheus` 容器 prom 的连接.

启动后由 [http://localhost:3000/login](http://localhost:3000/login) 进入登录页面. 默认的用户名, 密码都是 `admin`.

在添加数据源时, 可以直接使用 `--link` 指定的 `Prometheus` 容器别名 `prom`, 将 `URL` 设置为 `http://prom:9090`.

点击 `Save & Test` 保存并测试数据源是否可用. 成功后即可添加数据展示图表, 过程不再赘述.

到目前为止, 已经使用容器完成了数据收集, 存储和显示这几个服务的连接. 因为服务间具有依赖关系, 所以在启动时必须按照特定的顺序进行:
```
node_exporter --> prometheus --> grafana
```

可以看到启动过程已经有些麻烦. 那随着服务的增多, 以手动的方式控制多个容器会变得更加困难. 那有必要使用一个工具进行统一的管理了.

## Docker Compose
`Compose` 就是这样一个工具, 可以对组成一个应用的多个容器进行管理.

使用 `Compose` 有下面三个基本步骤:
1. 定义 `Dockerfile`, 使软件的配置和环境可以重复使用. 这里我们使用的都是现成的镜像, 也可以跳过这一步.
1. 在 `docker-compose.yml` 文件中定义组成应用的服务. 对我们来说, 就是要指定好容器间的连接和启动顺序.
1. 执行 `docker-compose up` 运行应用.

定义 `docker-compose.yml` 文件
```yml
version: '3.3'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    depends_on:
      - node_exporter
    links:
      - node_exporter:node1

  node_exporter:
    image: prom/node-exporter

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    links:
      - prometheus:prom
```
其中:
- `depends_on`: 定义服务的依赖关系, 决定了容器的启动顺序.
- `volumes`: 这里使用了相对目录, 引用的还是 [01-2](./01-2%20使用%20Docker%20在%20Ubuntu%20中部署%20Prometheus.md) 中定义的配置文件, 所以要把 `docker-compose.yml` 也放在同一目录下.
- 其余参数与 `docker run` 中的含义相同.

编辑好后 `docker-compose up -d` 启动服务.


### Compose links 配置选项
文档中提到:
> Links also express dependency between services in the same way as depends_on, so they determine the order of service startup.

说明 `links` 也能表示服务间的依赖关系. 那就去掉 `depends_on` 参数, 删除旧的服务 `docker-compose down` 后, 重新启动, 检查容器运行状态正常.
```
$ docker-compose ps
           Name                         Command               State           Ports         
--------------------------------------------------------------------------------------------
prometheus_grafana_1         /run.sh                          Up      0.0.0.0:3000->3000/tcp
prometheus_node_exporter_1   /bin/node_exporter               Up      9100/tcp              
prometheus_prometheus_1      /bin/prometheus --config.f ...   Up      0.0.0.0:9090->9090/tcp
```
