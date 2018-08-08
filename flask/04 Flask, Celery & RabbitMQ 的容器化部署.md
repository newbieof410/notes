# Flask, Celery & RabbitMQ 的容器化部署
> - 完整代码保存在该 [仓库 &raquo;](https://github.com/newbieof410/dockerize-flask-celery).
> - 项目结构参考 [The Flask Mega-Tutorial &raquo;](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xv-a-better-application-structure).

## 项目结构

```
├── app
│   ├── celery_worker
│   │   ├── __init__.py
│   │   └── tasks.py
│   ├── __init__.py
│   └── test_celery
│       ├── __init__.py
│       └── views.py
├── config.py
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── requirements.txt
```

当 `Flask` 与 `Celery` 整合使用时, 像其使用他插件一样, 通常会将 `Celery` 的配置信息放到 `Flask` 应用的配置文件中统一管理. 这时初始化 `Celery` 对象就需要从 `Flask` 对象中获取配置信息.
```Python
# app/__init__.py

celery = Celery(
    app.import_name,
    backend=app.config['CELERY_RESULT_BACKEND'],
    broker=app.config['CELERY_BROKER_URL']
)
celery.conf.update(app.config)
```
这样一来, 在初始化 `Celery` 前, 必须有一个 `Flask` 对象. 如果 `Flask` 项目采用的是单模块结构, 那么这么做没有问题: 只要在 `Flask` 初始化后, 再初始化 `Celery` 就好了. 但实际项目往往比较复杂, 需要使用到蓝图, 以工厂模式创建 `Flask` 对象, 这又会导致循环引用的问题.

```
flask_app --> some_blueprint --> celery_app --> flask_app
```

在工厂中先是要创建 `flask_app`, 接着注册 `blueprint`. 在某些 `blueprint` 中可能调用了 `Celery` 任务, 那么就要引入任务的定义. 而在任务的定义模块中又要引用 `Celery` 实例, 结果初始化这个实例又返回去要依赖 `Flask` 实例.

参考 [Miguel](https://blog.miguelgrinberg.com/post/using-celery-with-flask) 和 [Shulhi](http://shulhi.com/celery-integration-with-flask/) 的解决方法, 他们都初始化了两个 `Flask` 实例. 其中一个用于处理请求, 另一个只用于初始化 `Celery`, 提供任务执行时需要的应用上下文.

```python
# app/__init__.py

def create_app(config_name, register_blueprint=True):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if register_blueprint:
        from app.test_celery import test_celery as test_celery_blueprint
        app.register_blueprint(test_celery_blueprint)

    return app
```

这里对 `Flask` 工厂做了小的修改, 当初始化 `Celery` 需要一个 `Flask` 实例时, 可以设置这个实例不注册 `blueprint`, 就没有了后面的循环引用问题.

Celery worker 的初始化部分模仿了 [Miguel](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xv-a-better-application-structure) 蓝图的使用模式.

```Python
# app/celery_worker/__init__.py

from app import make_celery_app

celery = make_celery_app()

from app.celery_worker import tasks
```

把定义任务的模块写在末尾, 是为了任务能够正确注册, 同时也避免了循环引用.

在 `Celery` 启动后, 从输出信息中可以看到任务是否成功注册.
```
[tasks]
  . app.celery_worker.tasks.long_time_task
```

## Dockerfile
```dockerfile
FROM python:3.6-alpine

RUN pip install --upgrade pip
RUN pip install gunicorn

ENV INSTALL_DIR /home/flask-celery-example
RUN mkdir -p $INSTALL_DIR
WORKDIR $INSTALL_DIR

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app app
COPY config.py manage.py ./

EXPOSE 8000
USER nobody
ENTRYPOINT ["gunicorn"]
CMD ["--workers=1", "--bind=0.0.0.0:8000", "manage:app"]
```

`Docker` 镜像采用分层的方式构建. `Dockerfile` 则是镜像构建指令的集合, 每一条指令都是一个构建的步骤.

构建过程中, `daemon` 进程会用上一步的得到的镜像运行一个容器, 再从 `Dockerfile` 中取一条指令放在容器中执行, 执行完毕这个容器会被提交为一个新的中间层镜像. 因为每条指令都要放在容器中执行, 所以在文件开头一定要使用 `FROM` 指定基础镜像.

通过输出信息可以更好地理解构建过程.
```
Step 10/14 : COPY config.py manage.py ./
 ---> a6bd15e966a2
Step 11/14 : EXPOSE 8000
 ---> Running in 37783262d46c
Removing intermediate container 37783262d46c
 ---> 126bed54b9ad
Step 12/14 : USER nobody
 ---> Running in b8cc55a96fd1
Removing intermediate container b8cc55a96fd1
 ---> e05067bc6321
Step 13/14 : ENTRYPOINT ["gunicorn"]
 ---> Running in 57b3c62a706b
Removing intermediate container 57b3c62a706b
 ---> ef9405508581
Step 14/14 : CMD ["--workers=1", "--bind=0.0.0.0:8000", "manage:app"]
 ---> Running in 3e76ccf5425e
```

镜像的构建过程由上到下展开, 在构建过程中, `Docker` 会把中间的镜像缓存起来, 方便重用. 因此, 把最常用, 最不易变化的指令放在 `Dockerfile` 上面, 可以缩短镜像构建时间.

所以在上面的 `Dockerfile` 中, 就先安装了 `pip` 升级和 `gunicorn` 作为 `WSGI` 服务器, 然后才是构建应用的命令.

### COPY
`COPY` 的用法是 `COPY <src> <dest>`.

其中, 源文件路径是相对于构建上下文的相对路径. 上下文一般为 `Dockerfile` 所在目录的文件, 包含下层的所有子文件. 而目标路径既可以是绝对的, 也可以是相对的, 相对于 `WORKDIR` 中设置的路径.

注意到上面用了两种方法表示工作目录下, 分别是 `.` 和 `./`, 它们的效果是一样的.

复制 `app` 这个文件夹时, 目标位置没有使用 `.` 而是使用了 `app` 指定了一个文件名. 这是因为 `COPY` 复制的是文件夹中的所有内容, 而不包括外面的这层目录, 这一点和 `cp` 命令的效果不同.

### USER
在测试中看到警告:
```
RuntimeWarning: You're running the worker with superuser privileges: this is
worker_1  | absolutely not recommended!
```
这是因为默认容器以 `root` 身份运行. 既然不建议, 就使用命令 `USER nobody` 更改了要使用的用户. 后续命令都会在这个用户的权限下执行.

在一般情况下, 更改用户前需要保证用户存在, 如果不存在要使用 `adduser` 创建用户. 因为 `nobody` 是 `UNIX` 系统中的默认用户, 所以可以直接使用. 不过这个用户的权限比较小, 很多操作无法完成.

### ENTRYPOINT & CMD
在 `ENTRYPOINT` 中通常指定容器运行后默认执行的指令, 而在 `CMD` 中指定可变的参数.

## Docker Compose
```yaml
version: '3'
services:
  rabbit:
    image: rabbitmq:latest
    hostname: black-rabbit
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=admin-pass

  worker:
    build: .
    entrypoint: ["celery"]
    command: ["worker", "-A", "app.celery_worker", "--loglevel=info"]
    depends_on:
      - rabbit

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - rabbit
```
整个应用由三个服务组成, 分别是 `RabbitMQ`, 执行后台任务的 `worker` 和 `Flask` 应用.

一般在服务定义中至少要包含 `image` 或 `build` 两个配置中的一个. 使用 `image` 会从现有的镜像中构建服务, 而使用 `build` 则会根据指定的上下文构建一个镜像.

一个有趣的地方是, 上面用于构建 `app` 和 `worker` 的是同一个 `Dockerfile`. 一方面是因为 `task` 的定义和 `app` 位于同一个项目中. 但在另一方面, `task` 又承担着不同的角色: 用在 `worker` 中, 角色是任务的执行者; 用在 `app` 中, 则作为任务的发布者.

虽然它们可以使用同一个 `Dockerfile`, 但毕竟任务不同, 需要一定修改. 上面的 `worker` 就重写了 `entrypoint` 和 `command`, 覆盖了 `Dockerfile` 中启动服务器的命令, 变成启动工作进程. 而 `app` 使用的则是默认配置.

### expose & ports
在 `Dockerfile` 中使用 `EXPOSE` 命令可以将容器端口映射到主机, 而在 `Compose` 中, `expose` 指定的端口只能被相连接的服务所访问. 若要映射主机端口到容器, 应使用 `ports` 配置.

### 其他
使用 `docker-compose up` 会构建并启动应用. 在操作中发现, 有时修改了文件内容, 但更改并未得到应用, 这时可以使用 `--build` 参数重新构建镜像.

## 总结
这篇笔记中包括两方面内容. 一是如何将 `Celery` 应用到 `Flask` 应用中去, 二是如何把它们构建在容器中. 通过实际操作, 还加深了我们对 `Docker` 配置命令的了解.

## 参考链接
- [Dockerize a Flask, Celery, and Redis Application with Docker Compose](https://nickjanetakis.com/blog/dockerize-a-flask-celery-and-redis-application-with-docker-compose)
- [docker-cluster-with-celery-and-rabbitmq](https://github.com/tonywangcn/docker-cluster-with-celery-and-rabbitmq)
- [Celery integration with Flask](http://shulhi.com/celery-integration-with-flask/)
- [Celery and the Flask Application Factory Pattern](https://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern)
- [Celery Background Tasks](http://flask.pocoo.org/docs/1.0/patterns/celery/)
- [Best practices for writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#avoid-installing-unnecessary-packages)
- [Dockerfile reference](https://docs.docker.com/engine/reference/builder/)
- [Compose file version 3 reference](https://docs.docker.com/compose/compose-file/)
- [nobody](https://wiki.ubuntu.com/nobody)
