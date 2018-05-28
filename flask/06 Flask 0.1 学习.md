# Flask 0.1 学习
只要几行代码就能实现一个简单的 `Flask` 应用. 我们就以这段实例程序为线索, 看看 `Flask` 在背后都做了什么.
```python
from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"
```

## 初始化
第一步, 初始化 `Flask` 实例. 这一步需要提供应用所在的包或模块的名称, 所以在初始化时使用了 `__name__` 属性.
```python
def __init__(self, package_name):
    self.debug = False
    self.package_name = package_name
    self.root_path = _get_package_path(self.package_name)
    self.view_functions = {}
    self.error_handlers = {}
    self.before_request_funcs = []
    self.after_request_funcs = []
    self.template_context_processors = [_default_template_ctx_processor]
    self.url_map = Map()
    ...
```
`Flask` 搭了一个框架, 使我们只需关注业务逻辑的实现. 后面为空的几个属性就是需要我们实现的部分了.
- `view_functions` 存储视图方法
- `error_handlers` 保存错误处理方法
- `before/after_request_funcs` 在进入视图函数前和视图函数运行结束后执行的方法
- `url_map` 使用 `Werkzeug` 提供的 `Map` 对象, 用于存储 `URL` 到处理方法的映射规则.

## 设置路由
执行到 `@app.route("/")` 时, 我们的应用程序中就注册上了第一条路由规则, 和第一个视图方法.
```python
def route(self, rule, **options):
    def decorator(f):
        self.add_url_rule(rule, f.__name__, **options)
        self.view_functions[f.__name__] = f
        return f
    return decorator
```
`route` 方法会返回一个装饰器, 相当于执行了两个步骤:
1. 添加 "/" 到 "hello" 的对应关系
    ```python
    self.add_url_rule("/", "hello")
    ```
1. 将 hello 存入 view_functions 字典中, 保存了 "hello" 到 hello 的映射
    ```python
    self.view_functions["hello"] = hello
    ```

在 `add_url_rule` 中, 会设置 `view` 方法在默认情况下只服务 `GET` 请求. 路由映射会保存在 `url_map` 中, 一条映射至少要包含 `URL rule`, `methods` 和 `endpoint`.
```python
def add_url_rule(self, rule, endpoint, **options):
    options['endpoint'] = endpoint
    options.setdefault('methods', ('GET',))
    self.url_map.add(Rule(rule, **options))
```

## 运行
`Flask` 是一个符合 `WSGI` 规范的 `Web` 框架, 处在应用程序这一端. 按照规范, 应用程序必须是一个可调用对象, 需要接收两个参数:
1. `environ` 字典, 包含请求信息;
1. `start_response` 可调用对象, 返回响应头和状态码到服务器.

在运行 `Flask` 应用时, 需要把一个 `Flask` 实例, 通常叫做 `app`, 提供给服务器程序, 那么这个实例就一定是一个可调用对象了. 一个类的实例若要成为可调用对象, 需要在类内定义 `__call__` 方法, 之后才能像使用函数一样使用这个实例.

在 `Flask` 中, 可以找到 `__call__` 的定义,
```python
def __call__(self, environ, start_response):
    return self.wsgi_app(environ, start_response)
```
服务器收到请求后, 可以通过 `app(environ, start_response)` 和 `app.__call__(environ, start_response)` 两种方式调用应用程序.

在 `__call__` 中并没有实现请求处理逻辑, 而只是调用了 `wsgi_app`.
```python
def wsgi_app(self, environ, start_response):
    with self.request_context(environ):
        rv = self.preprocess_request()
        if rv is None:
            rv = self.dispatch_request()
        response = self.make_response(rv)
        response = self.process_response(response)
        return response(environ, start_response)
```
这么做, 在文档中写道, 是为了以下面的方式使用中间件.
```python
app.wsgi_app = MyMiddleware(app.wsgi_app)
```
并且, 在初始化的过程中, 就使用了一个中间件来提供对静态文件请求的支持.
```python
self.wsgi_app = SharedDataMiddleware(self.wsgi_app, {
    self.static_path: target
})
```

现在进入 `wsgi_app` 中, 在正式处理请求前, 需要调用 `request_context` 开启一个请求的上下文环境.
```python
def request_context(self, environ):
    return _RequestContext(self, environ)
```
可以看到 `request_context` 本身并不是一个上下文管理器, 而是返回了 `_RequestContext` 对象.
```python
class _RequestContext(object):

    def __init__(self, app, environ):
        self.app = app
        self.url_adapter = app.url_map.bind_to_environ(environ)
        self.request = app.request_class(environ)
        self.session = app.open_session(self.request)
        self.g = _RequestGlobals()
        self.flashes = None

    def __enter__(self):
        _request_ctx_stack.push(self)

    def __exit__(self, exc_type, exc_value, tb):
        if tb is None or not self.app.debug:
            _request_ctx_stack.pop()
```
从初始化方法中可以找到上下环境中所包含的信息:
- `app` 处理当前请求的 `Flask` 对象;
- `url_adapter` 根据请求上下文进行 `URL` 匹配;
- `request` 请求对象;
- `session` 会话对象;
- `g` 从名称上理解应该是与请求相关的全局变量;
- `flashes` 提示消息.

在开始执行 `with` 中的代码块之前, 上下文信息会被推入栈中, 执行完后再弹出.

构建好上下文后开始处理请求.
```python
def preprocess_request(self):
    for func in self.before_request_funcs:
        rv = func()
        if rv is not None:
            return rv
```
在该方法中, 会依次执行 `before_request_funcs` 中注册的方法, 而且执行顺序与注册顺序相同. 如果在处理过程中得到了非空的返回结果, 函数会立即返回, 开始构造响应 `make_response`.

```python
def make_response(self, rv):
    if isinstance(rv, self.response_class):
        return rv
    if isinstance(rv, basestring):
        return self.response_class(rv)
    if isinstance(rv, tuple):
        return self.response_class(*rv)
    return self.response_class.force_type(rv, request.environ)
```

`make_response` 可以处理四种类型的 `before_request_funcs` 和 `view` 方法的返回值:
1. `response_class` 返回值为响应对象, 不作处理直接返回;
1. `basestring` 返回值为字符串, 传入 `response_class` 构造响应对象;
1. `tuple` 返回值为元组, 传入 `response_class` 构造响应对象;
1. 最后一种情况没有做类型检查, 但是必须保证传入的参数类型为 `WSGI` 应用程序. 在方法内部会执行该应用, 得到响应对象并做类型转换.

```python
class BaseResponse(object):
    def __init__(self, response=None, status=None, ...):
        ...
```

## 参考资料
- [What is an 'endpoint' in Flask?](https://stackoverflow.com/a/19262349)
