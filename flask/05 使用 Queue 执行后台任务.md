# 使用 Queue 执行后台任务
在程序比较简单时, 可以在初始化 app 时, 启动几个工作线程执行后台任务. 这样做其实有一些缺点 (比如不能开启多个应用进程服务请求, 因为每初始化一个应用实例, 都会启动几个工作线程), 但了解一下线程的操作也无妨啊.

## 项目结构
用 `tree` 这个命令行工具显示出项目的文件结构, 如果有一些不需要显示的中间文件, 使用 `-I` 选项 ignore 掉.
```
.
├── app
│   ├── __init__.py
│   ├── models.py
│   ├── task_queue.py
│   ├── test
│   │   ├── __init__.py
│   │   └── views.py
│   └── worker.py
├── config.py
├── data.sqlite
├── manage.py
└── migrations
```
项目结构与之前相同, 其中和我们的任务有关的主要有这几个文件:
- `app/task_queue.py` 实现了一个任务队列;
- `app/worker.py` 负责完成队列中的任务;
- `app/__init__.py` 在这里关注任务队列是如何初始化的.

## task_queue
```python
from queue import Queue


class TaskQueue(Queue):

    def __init__(self, maxsize=0):
        super().__init__(maxsize)
        self.app = None
        self.workers = []

    def init_app(self, app):
        from app.worker import Worker

        self.app = app

        self.maxsize = app.config.get('MAX_QUEUE_SIZE', 0)
        self._init(self.maxsize)

        for i in range(app.config.get('WORKER_NUMBER', 1)):
            worker = Worker()
            worker.start()
            self.workers.append(worker)
```
任务队列是`生产者--消费者`模式中的基本组成部分. 担任生产者角色的线程会不时地产生任务, 处于消费者角色的线程负责处理任务, 任务的产生速度和处理速度并不一定能匹配, 所以需要一个中间的缓存. 任务产生后, 都先进入这个缓存区域, 排起队来等待服务.

队列处在中间地带, 在生产者这头, 还有消费者那头会被多个线程访问, 如果不对访问它的线程加以控制, 里面存储的内容就全乱套了. 这是因为高级语言的一步操作, 转换成 `CPU` 可以直接理解的机器语言往往就变成了许多步. 所以使用起来必须小心, 一个线程进行操作时, 要通过加锁阻止其他线程的访问.

要自己实现对这个缓冲区域有控制地访问实在有许多细节需要考虑, 好在标准库中就有现成的 `Queue` 可以使用. `Queue` 中已经实现了必要的加锁操作, 就算有多个线程同时操作, 也能保证结果的正确性.

直接使用继承就构建出了自己的 `TaskQueue`. 在初始化方法中, 通过指定 `maxsize` 来限制队列的长度. 又根据需要, 增加了 `app` 和 `workers` 两个属性. `app` 用来保存 `Flask` 的一份实例, 可以供 `worker` 使用, 提供应用上下文. `workers` 用来保存开启了几个工作线程.

下面又增加了 `init_app` 方法, 这模仿了一些 `Flask` 拓展的做法. 它们需要应用在实例化后, 调用该方法, 初始化应用, 使应用能与拓展配合工作. 而我们在这个方法中是对队列本身做必要的初始化, 包括: 一, 根据 `app` 的配置修改队列的长度; 二, 启动配置数目的工作线程.

在 `Queue` 的内部使用 `deque` 来表示队列,  它在 `_init()` 中创建, 修改队列长度不能只更改 `maxsize` 属性, 而要再次调用 `_init` 方法重新初始化队列.
```python
class Queue:
    def __init__(self, maxsize=0):
        self.maxsize = maxsize
        self._init(maxsize)
        ...

    def _init(self, maxsize):
        self.queue = deque()
```

## worker
```python
import threading
import time

from app import tq, db
from app.models import Record


class Worker(threading.Thread):

    def run(self):
        while True:
            item = tq.get()

            with tq.app.app_context():
                time.sleep(random.randrange(10, 30))
                record = Record(data=item)
                db.session.add(record)
                db.session.commit()
                print(item)
            tq.task_done()
```
新线程用 `Thread` 创建, 它有两种使用方式. 一种是在初始化时告诉它执行哪个可执行对象, 而这里使用了第二种方法, 通过继承, 在子类中重写 `run` 来实现.

在线程中执行一些操作经常会遇到这样的问题:
```
RuntimeError: No application found. Either work inside a view function or push an application context.
```
这是因为操作中需要用到与应用相关的信息, 比如 `app.config` 中的设置. 所以这里用数据库操作作为示例, 展示如何解决上下文的问题.

## 初始化
```python
# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.task_queue import TaskQueue
from config import config

db = SQLAlchemy()
tq = TaskQueue()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    tq.init_app(app)

    from app.test import test as test_blueprint
    app.register_blueprint(test_blueprint)

    return app
```
上面把任务队列作为全局变量放在 `create_app` 之外. 在 `manage.py` 中执行到
```python
from app import create_app, db
```
时, 就会进入 `app.__init__` 中, 实例化出 `tq`. 然后在调用 `create_app` 时, 再修改队列的长度, 开启工作线程.

## 使用
```python
# app/test/views.py

import queue

from flask import jsonify, request

from app import tq
from app.test import test


@test.route('/')
def index():
    try:
        tq.put(request.args.get('data', 'default'), timeout=2)
    except queue.Full:
        return jsonify(msg='queue is full, try later'), 400

    return jsonify(msg='request accepted')
```
现在, 就可以在视图中使用任务队列了. 收到请求后, 只要把任务放到队列中即可返回响应, 而不用等待任务完成. 默认情况下, 执行 `put` 操作时如果队列没有剩余空间, 那么 `put` 会被一直阻塞下去, 所以使用了 `timeout` 设置最多等多久.

## 结束运行
现在程序是可以跑起来了, 但想要结束时却发现必须按两次 `ctrl` + `c` 程序才能退出执行, 或者有时只是想使用命令行工具执行数据库操作, 执行完之后还要再按一次 `ctrl` + `c` 才能结束后台运行的线程. 这可不行, 还要再做一些修改.

### 修改 1
```python
class TaskQueue(Queue):

    def init_app(self, app):
        ...

        for i in range(app.config.get('WORKER_NUMBER', 1)):
            worker = Worker()
            worker.setDaemon(True)
            worker.start()
        ...
```
这里只加了一条语句, 就是在工作线程启动前, 调用了一下 `setDaemon()` 方法. 现在再试, 程序只要关一次就能结束了.

设置成 `daemon` 的作用是什么呢? 文档里是这么说的,
> A thread can be flagged as a “daemon thread”. The significance of this flag is that the entire Python program exits when only daemon threads are left.

就是说只有 `daemon` 线程结束后, 整个程序才会退出. 但这条说明好像与操作的结果并不一致, 因为接收到中断信号的是主线程, 而子线程是一个死循环, 本不该结束才对. 然后又找到了其他答案,
> A daemon thread will not prevent the application from exiting. The program ends when all non-daemon threads (main thread included) are complete.  
>  ...  
  the daemon threads are killed when the program exits.

结合起来看就明白多了. 首先, 程序运行后最先启动的是主线程, 它不是 `daemon` 线程. 子线程会继承父线程的 `daemon` 属性, 那么在主线程中启动的工作者线程也就不是 `daemon` 线程, 需要在启动前手动设置. 这样在主线程结束时, 子线程也会跟着结束. 如果没有设置子线程为 `daemon`, 最初的版本就是这种情况, 主线程结束后, 子线程还会继续运行.

### 修改 2
接着看往下看文档, 有一条提醒, 说 `daemon` 线程结束时可能无法正确地释放资源, 提示
> Daemon threads are abruptly stopped at shutdown. Their resources (such as open files, database transactions, etc.) may not be released properly. If you want your threads to stop gracefully, make them non-daemonic and use a suitable signalling mechanism such as an Event.


## 参考链接
- [queue — A synchronized queue class](https://docs.python.org/3.6/library/queue.html)
- [threading — Thread-based parallelism](https://docs.python.org/3.6/library/threading.html#threading.Thread.join)
- [atexit — Exit handlers](https://docs.python.org/3.6/library/atexit.html)
- [How can I add a background thread to flask?](https://stackoverflow.com/questions/14384739/how-can-i-add-a-background-thread-to-flask)
- [Is there any way to kill a Thread in Python?](https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python)
- [Terminate a multi-thread python program](https://stackoverflow.com/questions/1635080/terminate-a-multi-thread-python-program)
- [Cannot kill Python script with Ctrl-C](https://stackoverflow.com/a/11816038)
