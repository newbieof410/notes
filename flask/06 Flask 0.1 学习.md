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
- `before/after_request_funcs`
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

```python
def add_url_rule(self, rule, endpoint, **options):
    options['endpoint'] = endpoint
    options.setdefault('methods', ('GET',))
    self.url_map.add(Rule(rule, **options))
```

## 运行
```python
def __call__(self, environ, start_response):
    """Shortcut for :attr:`wsgi_app`"""
    return self.wsgi_app(environ, start_response)
```

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
