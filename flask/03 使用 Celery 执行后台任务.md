# 使用 Celery 执行后台任务
## 任务队列
`Task queue` 用于将任务分发到不同的线程或设备上运行, 对于 Web 应用来说, 它用来管理那些需要在 HTTP 请求响应循环外执行的后台任务.

在 `WSGI` 服务器中, 每个请求都由一个工作进程处理, 这个进程会被一直占用, 直到完成响应. 如果在这个进程中处理耗时很长的任务, 用完了工作进程, 那么就会使得后续的请求长时间得不到响应. 所以, 为了使服务器更快地响应, 一个好的办法就是把这些工作移到任务队列中, 进行异步地处理.

一些应用场景:
- 用做缓存. 如果一些数据库操作放在 HTTP 请求的处理中去执行需要占用过长的时间, 那么就可以在后台定期地执行这些操作, 当收到 HTTP 请求需要这些结果时, 就直接返回已经得到的结果, 而不是重新执行.
- 把大量独立的数据库插入操作分散开来, 而不是在同一时间执行.
- 定期聚合监测数据.
- 执行周期性的工作.

## Celery
`Celery` 是一个异步的任务队列. 虽然使用 `Queue` 也能简单实现类似的功能, 但是相比之下, `Celery` 的分布式架构可以使应用更易于拓展. `Celery` 主要有下面几个组件:
- 客户端: 产生后台任务
- 工作进程: 执行后台任务, 可以位于本地或远程设备.
- 消息代理: 客户端通过消息队列与工作进程通信. `Celery` 需要使用第三方的消息队列组件, 常用的有 `RabbitMQ` 和 `Redis`.
- 结果存储: 保存任务执行状态和结果.

## Celery 示例
`Celery` 简单示例.

### 定义 Celery 任务
只要在一个普通函数上加上 `Celery` 对象的 `task` 方法装饰, 如下面的 `@celery.task`, 即可作为 `Celery` 任务.
```python
#test_celery.py
import subprocess

from celery import Celery

# 第一个参数一般设置为模块名
# broker 和 backend 都设置为默认的 URL
celery = Celery('test_celery', broker='pyamqp://guest@localhost//',
                backend='rpc://')

@celery.task
def ls():
    try:
        subp = subprocess.run(['ls', '-l'], stdout=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        raise

    return subp.stdout.decode()
```
这里 `ls()` 的作用是执行 `ls -l` 命令并返回结果. 默认情况下 `Celery` 并不保存任务结果, 如要获取返回值, 必须在 `backend` 中指定保存位置.

### 启动工作进程
进入 `test_celery.py` 所在的文件夹, 执行
```
$ celery worker -A test_celery.celery --loglevel=info
```
- `celery worker` 启动工作进程
- `-A test_celery.celery` 指定 `Celery` 实例
- `--loglevel=info` 设置日志显示级别

如果添加成功, 在输出的 `tasks` 标签下会显示出设置的任务, 如下:
```
[tasks]
  . test_celery.ls
```

### 调用 `Celery` 任务
还是在相同目录下, 进入 `Python` 交互模式, 输入
```python
>>> from test_celery import ls
>>> ret = ls.delay()
>>> print(ret.result)
total 8
...
```
- `delay()` 方法用于调用任务, 返回值是一个 `AsyncResult` 对象.
- 由 `result` 属性可以得到任务的执行结果.
- 在相同目录下操作, 是为了使引用路径与设置的任务相同. 比如, 上面设置的任务为 `test_celery.ls`, 引用的语句就为 `from test_celery import ls`, 否则会产生错误 `Received unregistered task of type 'XXX'`

## 总结
在 `Celery` 中涉及到许多新的知识需要学习, 这里只大致走了一遍使用流程, 对它有了简单的了解. 内容还要继续补充.

## 参考资料
- [Task queues](https://www.fullstackpython.com/task-queues.html)
- [Using Celery With Flask](https://blog.miguelgrinberg.com/post/using-celery-with-flask)
- [First Steps with Celery](http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html)
