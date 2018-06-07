# 使用 Celery 执行周期任务

## 使用 Redis
`Redis` 是一种将数据以键值对形式存储于内存中的 `NoSQL` 数据库, 常用于存储 Web 应用会话, 临时数据或是作为任务队列的数据存储中介.

### 运行 Redis 容器
```
$ docker run -d -p 6379:6379 --name redis redis
```
为了便于在主机中测试, 把 `redis` 默认的 `6379` 端口与主机端口作了映射.

### 通过 redis-cli 连接

```
$ docker run -it --link redis:rds-srv --rm \
> redis redis-cli -h rds-srv -p 6379
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
- `--rm` 不带参数. 它的作用是使容器退出后就被自动删除.

  这样一来启动的容器就变成一次性的了, 那么以后如果只要容器运行一次做测试, 就可以使用这个选项.
- `redis-cli -h rds-srv -p 6379` 是 `redis` 客户端的启动命令.

  它指示客户端连接到 `rds-srv:6379` 这个位置上的 `redis` 服务. 这里之所以能使用域名来连接服务器依靠的是 `--link` 选项. 不过 `--link` 虽然还能使用, 但其实已经被废弃了, 还有更好的连接方法.

连接成功后会进入可以操作 `Redis` 的命令行界面.
```
rds-srv:6379>
```

### 使用 Python 连接

安装 `Redis` 的 `Python` 客户端 `redis-py`.
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

### Celery 配置
若要在 `Celery` 中使用 `redis` 来存储任务和结果, 需要安装额外的依赖文件.
```
pip install redis
```
配置示例.
```
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```
一般的 `URL` 规则为:
```
redis://:password@hostname:port/db_number
```

## 周期任务
一般的 `Celery` 后台任务要靠客户端来发起, 比如 `view` 方法在收到请求后发出一个在后台更新数据库的任务. 建立周期执行的任务的思路与之类似, 只不过任务不再由客户端触发, 而是交给一个专用的调度程序负责. 工作进程那一端无需特别设置, 它并不关心任务是由谁发起的.

### 添加任务
> 示例所使用的 [项目结构 &raquo;](https://github.com/newbieof410/dockerize-flask-celery)

`Celery` 中的任务调度程序叫做 `celery beat`. 它通过 `beat_schedule` 配置项来获取自己的工作安排: 按照什么时间间隔, 发起什么样的任务.

所以我们可以通过配置项来设置周期任务.
```python
# app/celery_worker/tasks.py

from app.celery_worker import celery

@celery.task
def test(arg):
    print(arg)

celery.conf.beat_schedule = {
    'hi-every-15-seconds': {
        'task': 'app.celery_worker.tasks.test',
        'schedule': 15.0,
        'args': ("hi",)
    },
}
```
在上面的例子中, 首先设置了一个简单的任务, 它会把输入参数打印出来. 接着把任务的执行说明记录在了配置选项中.

一个任务要以键值对的形式配置. key `hi-every-15-seconds` 是任务的名称. 在任务的设置中使用了三个基本选项:
1.  `task` 执行什么任务. 填入任务的引用路径.
1.  `schedule` 多长时间执行一次任务. 使用了 `15s` 的时间间隔.
1.  `args`: 任务参数. 必须以 `list` 或 `tuple` 的形式提供. **特别要注意**, 当只有一个参数时, 要写成 `["hi"]` 或 `("hi",)` 的形式.

还有一种方式是使用 `add_periodic_task` 方法. 该方法操作的也是 `beat_schedule` 配置项, 所以可以起到相同的效果.

```python
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(10.0, test.s('Hello'), name="hi-every-15-seconds")
```

### 运行任务
运行时需要启动两部分: 任务调度进程和工作进程.
1.  启动任务调度程序.
    ```
    $ celery -A app.celery_worker.celery beat
    ```
    工作进程可以有多个, 但是调度程序一定不能开多了. 因为它们之间没有通信机制, 开多了会导致发出重复的任务. 像这样采用集中式的任务管理也有它的好处, 就是可以省去在分布式架构中必须要考虑的同步问题.

1.  启动工作进程.
    ```
    $ celery -A app.celery_worker.celery worker -c 1 --loglevel=info
    ```

    默认情况下, `Celery` 会启动与 `CPU` 数目相同的工作进程. 要自己指定的话需要使用 `-c` 选项.

1.  运行时可能遇到下面的问题.
    ```
    Cannot mix new and old setting keys, please rename the
    following settings to the new format:

    CELERY_RESULT_BACKEND                -> result_backend
    ```
    这是因为从 4.0 版本开始, `Celery` 使用了新的以小写字母组织配置项的方式. 虽然仍支持旧式的配置信息, 但却不允许混合使用. 之前的配置项都放在 `Flask` 配置文件中, 使用的是旧式的大写表示方式, 而上面又使用了小写的 `beat_schedule`, 所以导致了问题. 因而只要统一地改为一种配置方式就可以了.

    
- 多队列
- 优先级

## Cheet Sheet
```shell
# 容器关闭后自动删除
$ docker run -it --rm ubuntu bash

# redis 客户端连接服务器
$ redis-cli -h rds-srv -p 6379

# 启动 Celery beat 和 worker
$ celery -A app.celery_worker.celery beat
$ celery -A app.celery_worker.celery worker -c 1 --loglevel=info
```

## 参考资料
- [Getting Started Using Celery for Scheduling Tasks](https://www.caktusgroup.com/blog/2014/06/23/scheduling-tasks-celery/)
- [Using Redis](http://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html#using-redis)
- [How to Use Redis with Python 3 and redis-py on Ubuntu 16.04](https://www.fullstackpython.com/blog/install-redis-use-python-3-ubuntu-1604.html)
- [redis](https://docs.docker.com/samples/library/redis/)
- [Periodic Tasks](http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html#periodic-tasks)
- [New lowercase settings](http://docs.celeryproject.org/en/latest/userguide/configuration.html#new-lowercase-settings)
