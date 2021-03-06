# Flask 0.1 学习
只要几行代码就能实现一个简单的 `Flask` 应用.
```python
from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"
```
我们就以这段示例程序为线索, 看看 `Flask` 在内部都做了什么.

## 自定义
首先, 是用户自定义的部分.

### 初始化
第一步, 初始化 `Flask` 实例. 在初始化时, 需要提供应用所在的包或模块的名称, `Flask` 使用这个参数来确定应用包含哪些资源文件. 如果像示例中一样是一个单模块的应用, 直接使用 `__name__` 就可以了. 而如果在大型项目中, 将应用拆成了多个模块, 就应该使用最外层包的名称.

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

`Flask` 提供了一个框架, 它接收来自服务器的请求, 经过处理后将结果返回, 其中只有怎么处理需要用户自定义. 从初始化的过程就可以找到需要自定义的部分:
- `view_functions` 视图方法, 请求的具体处理逻辑;
- `error_handlers` 错误处理方法;
- `before/after_request_funcs` 在进入视图函数前和视图函数运行结束后执行的方法;
- `url_map` 使用 `Werkzeug` 提供的 `Map` 类, 存储 `URL` 到处理方法的映射规则.

### 设置路由
第二步, 设置路由. 执行到 `@app.route("/")` 时, 应用程序中就注册上了第一条路由规则, 和第一个视图方法.
```python
def route(self, rule, **options):
    def decorator(f):
        self.add_url_rule(rule, f.__name__, **options)
        self.view_functions[f.__name__] = f
        return f
    return decorator
```
`route` 方法返回了一个装饰器, 在装饰器中会执行两个步骤:
1. 添加 `"/"` 到 `"hello"` 的对应关系;
    ```python
    self.add_url_rule("/", "hello")
    ```
1. 将 `hello` 存入 `view_functions` 字典中, 保存了 `"hello"` 到 `hello` 的映射.
    ```python
    self.view_functions["hello"] = hello
    ```

由上面的执行过程, 可以得到 `URL` 到视图方法的映射关系:
```
URL("/") ---> endpoint("hello") ---> view(hello)
```
它们中间由 `endpoint` 相连接. 可是为什么要使用一个中间层 `endpoint` , 而不直接由 `URL` 映射到 `view` 方法呢? 这是因为如果使用了蓝图, 在不同的蓝图中可能会出现名称相同的视图方法, 也就无法确定映射关系了. 但是使用了 `endpoint`, 只要保证它的唯一性, 就能解决这个问题.

再看 `add_url_rule` 方法, 它会设置 `view` 在默认情况下只服务 `GET` 请求, 将路由映射保存在 `url_map` 中. 从方法的参数可以推测出, 一条映射至少要包含 `URL rule`, `methods` 和 `endpoint` 三个部分.
```python
def add_url_rule(self, rule, endpoint, **options):
    options['endpoint'] = endpoint
    options.setdefault('methods', ('GET',))
    self.url_map.add(Rule(rule, **options))
```

### 小结
程序运行到这里就执行完了用户定义的部分. 可以看到示例程序并没有对 `before/after_request_funcs` 和 `error_handlers` 这两部分作定义, 说明它们并不是必需的.

## 运行
`Flask` 是一个符合 `WSGI` 规范的 `Web` 框架, 处在应用程序这一端. 按照规范, 应用程序必须是一个可调用对象, 需要接收两个参数:
1. `environ` 字典, 包含请求信息;
1. `start_response` 可调用对象, 返回响应头和状态码到服务器.

### 可调用对象
在运行 `Flask` 应用时, 需要把一个 `Flask` 实例, 也就是示例中的 `app`, 提供给服务器程序, 那么这个实例就一定是一个可调用对象了. 一个类的实例若要是可调用的, 就需要在类内定义 `__call__` 方法, 之后才能像使用函数一样使用这个实例.

在 `Flask` 中, 可以找到 `__call__` 的定义,
```python
def __call__(self, environ, start_response):
    return self.wsgi_app(environ, start_response)
```

这里就看到 `WSGI` 的影子了. 服务器收到请求后, 可以通过 `app(environ, start_response)` 和 `app.__call__(environ, start_response)` 两种方式调用应用程序.

不过在 `__call__` 中并没有实现请求处理逻辑, 只是调用了 `wsgi_app`.
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

这样的话, 如果要增加中间件, 就可以使用下面的方式.
```python
app.wsgi_app = MyMiddleware(app.wsgi_app)
```

并且在初始化的过程中, 就使用了一个中间件来提供对静态文件请求的支持.
```python
self.wsgi_app = SharedDataMiddleware(self.wsgi_app, {
    self.static_path: target
})
```

### 构建请求上下文

现在进入 `wsgi_app` 中. 在正式处理请求前, 需要调用 `request_context` 开启一个请求的上下文环境.
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

在类中有 `__enter__` 和 `__exit__` 两个方法, 所以它才是真正的上下文管理器.

再来看它的初始化方法, 可以找到上下环境中所包含的信息:
- `app` 处理当前请求的 `Flask` 对象;
- `url_adapter` 根据请求上下文进行 `URL` 匹配;
- `request` 请求对象;
- `session` 会话对象;
- `g` 全局变量;
- `flashes` 提示消息.

在开始执行 `with` 中的代码块之前, 上下文信息会被推入栈中, 执行完后再弹出.

### 请求预处理

构建好上下文后开始处理请求. 但是在进入视图函数前, 需要先执行请求的预处理方法.

```python
def preprocess_request(self):
    for func in self.before_request_funcs:
        rv = func()
        if rv is not None:
            return rv
```
在该方法中, 会依次执行 `before_request_funcs` 中注册的方法, 而且执行顺序与注册顺序相同.

如果在处理过程中得到了非空的返回结果, 函数会立即返回, 跳过请求分发, 执行 `make_response` 构造响应对象. 利用这一机制, 就可以将一些请求拦截在视图方法之外. 应用场景如, 在正式处理请求前, 先进行身份和权限的验证.

### 请求分发

通过请求预处理后, 开始分发请求, 即根据请求信息, 执行对应的视图方法.

```python
def dispatch_request(self):
    try:
        endpoint, values = self.match_request()
        return self.view_functions[endpoint](**values)
    except HTTPException, e:
        handler = self.error_handlers.get(e.code)
        if handler is None:
            return e
        return handler(e)
    except Exception, e:
        handler = self.error_handlers.get(500)
        if self.debug or handler is None:
            raise
        return handler(e)
```

#### 请求匹配
从栈顶得到 `URL` 匹配对象, 查找匹配的 `endpoint`. 匹配参数由 `environ` 中获得.
```python
def match_request(self):
    rv = _request_ctx_stack.top.url_adapter.match()
    request.endpoint, request.view_args = rv
    return rv
```
匹配成功, 会得到 `endpoint` 与传入视图方法的参数, 参数是从 `URL` 中解析出来的. 不过匹配也可能产生以下异常:
- `NotFound`
- `MethodNotAllowed`
- `RequestRedirect`

#### 执行视图方法
有了 `endpoint` 就能找到对应的视图方法, 再传入请求参数, 视图开始执行.

```python
self.view_functions[endpoint](**values)
```

这里 `values` 的使用方式说明它是一个字典对象, 在函数调用中使用 `**values` 会将之转换为关键字参数, 即 `kwargs=value` 的形式.

#### 异常处理
在请求匹配的过程中, 会产生匹配失败的异常, 这一类的异常均继承自 `HTTPException`; 而在视图方法执行过程中, 还可能由于语法错误, 逻辑问题等造成其他的异常, 这一类异常会被通用的 `Exception` 捕获.
```python
except HTTPException, e:
    handler = self.error_handlers.get(e.code)
    if handler is None:
        return e
    return handler(e)
except Exception, e:
    handler = self.error_handlers.get(500)
    if self.debug or handler is None:
        raise
    return handler(e)
```

捕获到异常后, 会根据 `HTTP` 响应码查找对应的异常处理方法. 异常处理方法在初始时为空, 可以由我们使用 `errorhandler` 自定义.

```python
def errorhandler(self, code):
    def decorator(f):
        self.error_handlers[code] = f
        return f
    return decorator
```

这个方法十分简单. 它会返回一个装饰器, 作用只是把自定义的错误处理方法记录到 `error_handlers` 中.

在实现错误处理方法时有一点需要注意: 必须接收异常作为参数. 这可以从调用方式 `handler(e)` 看出来, 不论在处理过程中是否使用了该参数.

如果没有找到对应的处理方法也不用担心, 这时会直接将异常返回. 因为 `HTTPException` 本身即可作为响应对象, 提供了默认的处理方式, 比如返回默认的 `404` 页面, 所以才不会出问题.

### 构造响应

经过了预处理和请求分发, 最终会得到一个处理结果. 不论这个结果是来自预处理方法, 视图方法, 或是异常处理方法, 都会使用统一的方式把它构造为一个响应对象.

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

`make_response` 可以处理四种类型的处理结果或返回值:
1. `response_class` 响应对象, 不作处理直接返回;
1. `basestring` 字符串, 传入 `response_class` 构造响应对象;
1. `tuple` 元组, 传入 `response_class` 构造响应对象;
1. 最后一种情况没有做类型检查, 但是必须保证传入的参数类型为 `WSGI` 应用程序. 在方法内部会执行该应用, 得到响应对象并做类型转换.

`response_class` 继承自 `BaseResponse`. 在它的初始化方法中, 第一个参数是 `response`, 可接受类型为字符串或可迭代对象, 代表响应内容; 第二个参数是 `status`, 既可以只是一个整数, 代表状态码, 也可以为状态码和原因短语组成的字符串. 因为这些参数都带有默认值, 所以才能支持在 2, 3 两种情形下, 以不同的方式创建响应.
```python
class BaseResponse(object):
    def __init__(self, response=None, status=None, ...):
        ...
```

在第 3 中情况下, 使用了 `*` 操作符调用初始化方法. 当 `*` 出现在函数调用中时, 作用为解包, 即将作为整体的 `tuple` 或 `list` 中的元素, 一个个拿出来作为位置参数. 上面见过的 `**` 操作符用于将字典拆分为关键字参数.

在这一部分可以看到 `Flask` 对响应的构建过程提供了很大的灵活性, 这种灵活性通过判断参数类型和提供默认值来实现.

### 响应再处理
在得到响应后, 返回给服务器前, 还需要对响应做再次加工.
```python
def process_response(self, response):
    session = _request_ctx_stack.top.session
    if session is not None:
        self.save_session(session, response)
    for handler in self.after_request_funcs:
        response = handler(response)
    return response
```

#### 保存 session
首先要从请求上下文中取出 `session` 对象, 由 `open_session` 方法获得.
```python
def open_session(self, request):
    key = self.secret_key
    if key is not None:
        return SecureCookie.load_cookie(request, self.session_cookie_name,
                                        secret_key=key)
```

方法中的 `SecureCookie` 来自 `Werkzeug` 工具库. `load_cookie` 作用是将 `cookie` 字符串从请求对象中取出, 反序列化并加载为 `SecureCookie` 对象.

所以, 可以知道 `Flask` 中的 `session` 是使用 `cookie` 技术实现的, 当然也就存储在客户端.

如果使用了 `cookie`, 就需要将 `cookie` 内容附到 `HTTP` 响应头中. 具体来说, 服务端会使用 `Set-Cookie` 首部通知客户端浏览器保存 `cookie` 内容. 相应地, 为使 `cookie` 正常工作, 客户端浏览器必须允许 `cookie` 的使用.

```python
def save_session(self, session, response):
    if session is not None:
        session.save_cookie(response, self.session_cookie_name)
```

#### 请求后处理
这一步与请求预处理过程相同. 只是自定义的处理函数需要接收响应对象作为参数, 并返回处理后的响应对象.

### 返回响应
终于到了最后一步: 返回响应.
```python
return response(environ, start_response)
```

我们已经知道 `response` 是一个对象, 这里能像函数一样使用, 说明它一定是可调用的.

`response` 来自 `Werkzeug` 中的 `Response` 类, 它的一个基类是 `BaseResponse`. 直接找到 `__call__` 方法.

```python
def __call__(self, environ, start_response):
    app_iter, status, headers = self.get_wsgi_response(environ)
    start_response(status, headers)
    return app_iter
```

其中做了三件事:
1. 使用 `get_wsgi_response` 方法得到响应主体内容, 状态及响应头;
1. 调用 `start_response` 返回状态和响应头;
1. 返回响应主体.

标准的 `WSGI` 应用执行步骤.

### 小结
看到这里, `Flask` 就完成了在一次请求过程中需要做的工作. 然后处理结果会返回到服务器, 由服务器生成响应.

可以得到 `Flask` 大致的处理流程如下.
<div align="center"> <img src="./img/06-Flask-workflow.png"/> </div><br>

## 其他
### Context Stack

使用 `werkzeug` 提供的中间件, 多个 `Flask` 应用 (甚至和 `Django` 应用) 可以组合起来使用.

```python
from werkzeug.wsgi import DispatcherMiddleware
from frontend_app import application as frontend
from backend_app import application as backend

application = DispatcherMiddleware(frontend, {
    '/backend':     backend
})
```

这时多个应用运行在同一个解释器进程中. 那么问题来了: `Flask` 中有几个特殊的变量可以全局使用, 比如 `current_app` 和 `request`, 它们在使用时和当前的应用紧密相关, 如果我实例化了多个应用, `Flask` 是怎样把这些全局变量与应用对应起来的呢?

从代码中可以看到上下文存储在栈结构中.
```python
_request_ctx_stack = LocalStack()
current_app = LocalProxy(lambda: _request_ctx_stack.top.app)
request = LocalProxy(lambda: _request_ctx_stack.top.request)
session = LocalProxy(lambda: _request_ctx_stack.top.session)
g = LocalProxy(lambda: _request_ctx_stack.top.g)
```

每当应用被调用时, 处理过程会自动地在当前的上下文中执行.
```python
class Flask:

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        with self.request_context(environ):
            ...
```

再回到多应用的情形, 即使是在同一个进程中, 当需要哪个应用处理时, 就把那个应用的上下文压入栈中, 后面再使 `current_app` 等全局变量时, 它们会由栈顶获取信息, 得到的自然是当前应用的上下文.

<div align="center"> <img src="./img/06-Flask-stack.png"/> </div><br>

正因为这样, 我们在编写视图函数时才不需要关注上下文栈的存在, 可以直接使用上面的全局变量.

但是在另外一些情况下, 应用不是以 `WGSI` 应用的形式被调用的, 它不处在一个请求响应循环中, 这时就需要手动管理上下文. 例如:
- 在命令行中操作应用的数据库;
- 在后台线程中更新应用数据库;
- 在测试中模拟请求.

在 `0.1` 版本中只有一个请求上下文栈, 而在后续的更新中又进一步划分出应用上下文, 分别存储不同层面的信息.
- 请求上下文: `HTTP` 请求相关数据;
- 应用上下文: 数据库连接, 应用配置等应用层数据.

应用上下文可以单独使用, 而在使用请求上下文时会推入一个对应的应用上下文.

### Local Objects

栈的使用保证了多应用组合工作时上下文不至于混乱. 现在考虑另一个问题: 在多线程的环境下, 每个请求交给一个应用线程去处理, 而像 `request` 等全局变量对每个线程都是可见的, 那要如何保证每个线程拿到的 `request` 都是自己的?

`Flask` 应用当然可以多线程工作, 同时上下文能得到有序管理, 这依靠的是它所使用的 `LocalStack` 对象. 而 `LocalStack` 又依赖于 `Local` 对象, 所以就先来看看它是如何定义的.

```python
class Local(object):
    __slots__ = ('__storage__', '__ident_func__')

    def __init__(self):
        object.__setattr__(self, '__storage__', {})
        object.__setattr__(self, '__ident_func__', get_ident)

    def __getattr__(self, name):
        try:
            return self.__storage__[self.__ident_func__()][name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        ident = self.__ident_func__()
        storage = self.__storage__
        try:
            storage[ident][name] = value
        except KeyError:
            storage[ident] = {name: value}

    def __delattr__(self, name):
        try:
            del self.__storage__[self.__ident_func__()][name]
        except KeyError:
            raise AttributeError(name)

    ...
```
`Local` 中有一个字典用于存储各线程的数据, 数据存放在当前线程的 `id` 下. 取数据时, 先由 `get_ident` 方法获取 `id`, 再根据 `id` 使用自己的存储空间.

所以 `Local` 对象就像一个公共的储物柜, 每个线程都有一把钥匙, 使用这把钥匙只能打开自己的柜子.

<div align="center"> <img src="./img/06-LocalStack.png"/> </div><br>

说起来有些麻烦, 但使用起来却很方便, 因为每个线程的空间是 `Local` 帮我们找到的, 使我们可以像操作普通对象一样操作 `Local` 中的属性.

为了实现这个效果, `Local` 中重写了 `__setattr__()` 和 `__getattr__()` 方法. 在设置属性或获取属性时就是调用的这两个方法.

```Python
lcl = Local()
lcl.name = 'Atom' # Equals to lcl.__setattr__('name', 'Atom')
print(lcl.name) # Equals to print(lcl.__getattr__('name'))
```

默认情况下, 实例的属性存储在 `__dict__` 字典中, 而在 `Local` 中换了一个名字, 叫 `__storage__`. 不过 `__storage__` 本身也是对象的一个属性, 总不能自己存在自己里面, 而且它应该是为所有线程共同访问的, 所以在初始化时要使用默认的方法设置这个属性.

判断当前 "线程" 有两种方法. 如果使用了 `greenlet`, 就使用它的 `id`, 否则使用 `thread` 的 `id`.
```Python
try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident
```

再看 `LocalStack` 就明白了. 在它的内部有一个 `Local` 对象, 每个线程都在公共的 `Local` 中保存自己的上下文栈, 从而实现了线程间上下文的隔离.

还可以看到栈只不过是用列表来存储的.
```Python
class LocalStack(object):

    def __init__(self):
        self._local = Local()

    def push(self, obj):
        rv = getattr(self._local, 'stack', None)
        if rv is None:
            self._local.stack = rv = []
        rv.append(obj)
        return rv

    def pop(self):
        stack = getattr(self._local, 'stack', None)
        if stack is None:
            return None
        elif len(stack) == 1:
            release_local(self._local)
            return stack[-1]
        else:
            return stack.pop()

    @property
    def top(self):
        try:
            return self._local.stack[-1]
        except (AttributeError, IndexError):
            return None

    ...
```

### Local Proxy

我们已经知道了应用的上下文存储在栈结构中, 而且每个线程中的栈都是隔离的, 不会相互影响. 最后, 再来看看用于表示全局变量的 `LocalProxy` 又是怎么设计的.

```Python
current_app = LocalProxy(lambda: _request_ctx_stack.top.app)
request = LocalProxy(lambda: _request_ctx_stack.top.request)
session = LocalProxy(lambda: _request_ctx_stack.top.session)
g = LocalProxy(lambda: _request_ctx_stack.top.g)
```

在全局变量的定义中使用了匿名函数作为参数, 作用是从上下文栈顶取出实际操作的对象.

```Python
class LocalProxy(object):

    __slots__ = ('__local', '__dict__', '__name__', '__wrapped__')

    def __init__(self, local, name=None):
        object.__setattr__(self, '_LocalProxy__local', local)
        object.__setattr__(self, '__name__', name)
        if callable(local) and not hasattr(local, '__release_local__'):
            # "local" is a callable that is not an instance of Local or
            # LocalManager: mark it as a wrapped function.
            object.__setattr__(self, '__wrapped__', local)
```
在类属性 `__slots__` 中定义了一个实例属性 `__local`, 而在初始化方法中却设置了 `_LocalProxy__local`, 这两个其实指的是同一个属性. 这是 `Python` 的语言特性, 叫做 `name mangling`, 为避免这一类属性意外被外部修改增加了一层保护.

在使用全局变量时, 比如 `current_app`, 操作的并不是真正的 `Flask` 应用对象, 而是 `app` 的一个代理. 代理再通过初始化时提供的方法, 实时地找到当前上下文中实际被操作的对象. 就保证了不同的应用实例在处理时, 通过 `current_app` 能得到正确的应用实例.

对代理的大部分操作都会转发到实际的操作对象上去, 所以代理基本可以当作实际要操作的对象一样使用.

```Python
    def _get_current_object(self):
        if not hasattr(self.__local, '__release_local__'):
            return self.__local()
        try:
            return getattr(self.__local, self.__name__)
        except AttributeError:
            raise RuntimeError('no object bound to %s' % self.__name__)

    @property
    def __dict__(self):
        try:
            return self._get_current_object().__dict__
        except RuntimeError:
            raise AttributeError('__dict__')

    ...

    __setattr__ = lambda x, n, v: setattr(x._get_current_object(), n, v)
    __delattr__ = lambda x, n: delattr(x._get_current_object(), n)
    __str__ = lambda x: str(x._get_current_object())

    ...
```

再来通过图示理解 `LocalProxy` 的作用.
<div align="center"> <img src="./img/06-LocalProxy.png"/> </div><br>

### 小结
简单总结一下三种 `Local` 对象的作用.

- `Local`

  使全局变量在多线程环境下能被安全使用. 具体做法是在存取数据时判断当前所在的线程, 然后获取对应线程的数据.

  这里的线程既可以是常规线程, 也可以是 `greenlet`.

  根据线程 `id` 取值有一个缺点: 后来的使用者数据会被之前的使用者数据污染. 所以在更换使用者时要主动清空遗留的数据.

- `LocalStack`

  建立在 `Local` 上的栈结构.

- `LocalProxy`

  `Local` 的代理, 会把操作转发到实际的对象上去.

  多个代理可以共用一个 `Local` 存储数据, 方便管理.

  另外可以通过可调用对象初始化代理, 告诉它如何找到实际操作的对象.


## 参考资料
- [What is an 'endpoint' in Flask?](https://stackoverflow.com/a/19262349)
- [Understanding kwargs in Python](https://stackoverflow.com/a/1769475)
- [What is the purpose of Flask's context stacks?](https://stackoverflow.com/questions/20036520/what-is-the-purpose-of-flasks-context-stacks/20041823#20041823)
- [Flask 的 Context 机制](https://blog.tonyseek.com/post/the-context-mechanism-of-flask/)
- [Application Dispatching](http://flask.pocoo.org/docs/1.0/patterns/appdispatch/#application-dispatching)
- [Flask 源码解析: 上下文](http://cizixs.com/2017/01/13/flask-insight-context)
- [Context Locals](http://werkzeug.pocoo.org/docs/0.14/local/)
