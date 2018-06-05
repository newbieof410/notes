# 使用 Celery 执行周期任务
`Redis` 是一种将数据以键值对形式存储于内存中的 `NoSQL` 数据库, 常用于存储 Web 应用会话, 临时数据或是作为任务队列的数据存储中介.

## 运行 Redis 容器

```
$ docker run -d -p 6379:6379 --name redis redis
```
为了便于在主机中测试, 把 `redis` 默认的 `6379` 端口与主机端口作了映射.

## 通过 redis-cli 连接

```
$ docker run -it --link redis:rds-srv --rm redis redis-cli -h rds-srv -p 6379
```
这条命令比较复杂, 我们把它分解开来看. 先来了解 `run` 命令的用法.
```
docker run [OPTIONS] IMAGE [COMMAND] [ARG...]
```
可以分为三个部分,
1. `IMAGE` 是必须要有的, 它告诉 `docker` 使用哪个镜像运行容器;
1. 如果需要设置容器如何运行, 就要用到 `OPTIONS` 选项;
1. 容器运行起来后可以在其中执行一些命令, 命令和参数通过 `COMMAND` 与 `ARG` 指定.

所以找到 `IMAGE` 就能把上面的长命令分解开来了. `redis redis-cli` 这一部分比较容易让人混淆, 因为看上去 `redis` 像是前面 `--rm` 的参数. 但是再仔细分析一下就会发现, 如果 `redis-cli` 是镜像, 那后面的 `-h` 应该就是命令, 可是它显然是一个参数. 这样镜像就只能是 `redis` 了.

命令中有一些没有见过的选项需要了解,
- `--rm` 它的作用是使容器退出后就被自动删除.

  这样一来启动的容器就变成一次性的了, 那么以后如果只要容器运行一次做测试, 就可以使用这个选项.
- `redis-cli -h rds-srv -p 6379` 是 `redis` 客户端的启动命令.

  它指示客户端连接到 `rds-srv:6379` 这个位置上的 `redis` 服务. 这里之所以能使用域名来连接服务器依靠的是 `--link` 选项. 不过 `--link` 虽然还能使用, 但其实已经被废弃了, 还有更好的连接方法.

连接成功后会看到,
```
$ docker run -it --link redis:rds-srv --rm redis redis-cli -h rds-srv -p 6379
rds-srv:6379>
```

## 使用 Python 连接

安装 `redis-py`.
```
pip install redis
```

进入 `Python` 的交互界面.
```python
>>> import redis
>>> # 获取连接
>>> redis_db = redis.StrictRedis(host="localhost", port=6379, db=0)
>>> # 获取数据库中的 keys
>>> redis_db.keys()
[]
```
通过执行获取数据操作时是否出现了异常, 就可以判断连接是否成功了.


- 多队列
- 优先级

- `celery` 配置

  ```
  CELERY_BROKER_URL = 'redis://localhost:6379/0'
  CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
  ```
  `URL` 规则.


## 参考资料
- [Getting Started Using Celery for Scheduling Tasks](https://www.caktusgroup.com/blog/2014/06/23/scheduling-tasks-celery/)
- [Using Redis](http://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html#using-redis)
- [How to Use Redis with Python 3 and redis-py on Ubuntu 16.04](https://www.fullstackpython.com/blog/install-redis-use-python-3-ubuntu-1604.html)
- [redis](https://docs.docker.com/samples/library/redis/)
