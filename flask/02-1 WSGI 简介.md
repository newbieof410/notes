# WSGI
> `WSGI` 代表 `Web` 服务网关接口. 它是一个规范, 描述了 `Web` 服务器和 `Web` 应用程序之间应该如何通信, 还有 `Web` 应用程序间应该如何串联起来处理请求.

## 简介
- `WSGI` 不是服务器, 不是 `python` 模块, 不是一种框架, 也不是 `API` 或者某种软件. 它只是一种接口规范, 用于服务器和应用程序间的通信.
- 遵循这一规范编写的应用, 框架或工具集可以运行在任意一种遵循这种规范的服务器上, 反过来也一样.
- 符合 `WSGI` 规范的应用可以相互叠加. 那些夹在中间的叫做中间件, 必须同时实现应用端和服务端的接口. 对于构建在它之上的应用来说, 它相当于服务器, 而对于它之下的应用或服务器而言又是一个应用程序.
- 符合 `WSGI` 规范的服务器仅仅接受来自与客户端的请求, 再把请求转给应用程序, 最后把应用程序处理后的响应返回给客户端. 其他细节的处理都交由应用程序或中间件完成.

## 应用接口
- `WSGI` 应用接口的实现是一个可调用对象, 也即一个函数, 对象方法或者是包含 `object.__call__()` 方法的类或实例对象.
- 这个可调用对象必须接收两个位置参数:
  - 一个字典对象, 包含类似 `CGI` 中的变量;
  - 一个回调函数, 应用程序用它来发送 `HTTP` 状态码和报头等信息给服务器
- 最后, 这个可调用对象要返回响应体给服务器, 结构是用可遍历对象包裹的一些字符串对象.
- 应用框架
  ```python
  # 这里用函数作为应用接口
  # environ 是一个字典, 由服务器根据用户请求产生
  # start_response 是回调函数, 接收 HTTP 状态码和头部信息作为参数
  def application (environ, start_response):

    response_body = 'Request method: %s' % environ['REQUEST_METHOD']

    status = '200 OK'

    # HTTP 报头信息格式 [(Header name, Header value)]
    response_headers = [
      ('Content-Type', 'text/plain'),
      ('Content-Length', str(len(response_body)))
    ]

    # 发送响应头
    start_response(status, response_headers)

    # 返回响应体
    return [response_body]
  ```

## 环境变量字典
- 环境变量字典由服务器产生, 其中的数据是对客户请求处理后得到的 `CGI` 风格的变量. 下面这段脚本会输出整个字典中的内容.
  ```python
  #! /usr/bin/env python

  # Python 自带的 WSGI 服务器
  from wsgiref.simple_server import make_server

  def application (environ, start_response):

    # 对环境变量字典中的键值对排序, 并转换为字符串
    response_body = [
      '%s: %s' % (key, value) for key, value in sorted(environ.items())
    ]
    response_body = '\n'.join(response_body)

    status = '200 OK'
    response_headers = [
      ('Content-Type', 'text/plain'),
      ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)

    return [response_body]

  # 实例化服务器
  httpd = make_server (
      'localhost', # 主机名
      8051, # 监听的端口
      application # 应用程序对象
  )

  # 等待处理一个请求, 完成后退出
  httpd.handle_request()
  ```

## 可遍历响应对象
- 在上面的例子中, 如果把
  ```python
  return [response_body]
  ```
  改为
  ```python
  return response_body
  ```
  仍然可以正常运行, 但速度可能变慢. 因为字符串本身就是可遍历对象, 修改后就从将字符串整个返回给客户端, 变为逐个字符地返回. 所以为了提高性能, 要将响应内容包起来, 使它成为一个整体.
- 如果响应体中包含多个字符串, 那么响应体的长度会是所有这些字符串长度之和.

## 服务器端
- 服务器必须提供上面提到的 `environ` 字典和 `start_response` 函数.
- 服务器通过调用 `web` 应用接口程序来把请求传入应用中.
  ```python
  iterable = app(environ, start_response)
  for data in iterable:
     # send data to client
  ```
- 应用程序调用 `start_response` 生成响应头, 并负责生成 `iterable` 中的响应体.
- 服务器再把响应头和体通过 `HTTP` 返回给客户端.

## 中间件
- 一个中间件示例, 将下层应用(或中间件)的响应内容改为首字母大写.
  ```python
  class Upperware:

    def __init__(self, app):
        self.wrapped_app = app

    def __call__(self, environ, start_response):
        response_body = []
        for data in self.wrapped_app(environ, start_response):
            response_body.append(data.upper())
        return response_body
  ```

## 示例
- [02-2 WSGI_example.py](./02-2%20WSGI_example.py) 中是应用程序和中间件的简单示例. 可以直接与符合 `WSGI` 标准的服务器组合使用. 例如:
  ```
  gunicorn -b localhost:8080 WSGI_example:application
  ```
- **要注意**:
  - 响应需要转换为 `byte` 类型.
  - 在中间件增加内容后要修改应用返回的 `Content-Length`

## 相似概念
- **`uwsgi`**: 是一种 `uWSGI` 使用的二进制协议, 用于数据传输.
- **`uWSGI`**: 是一个应用服务器, 采用可插拔的架构以支持多语言和平台.

  因为其上开发出来的第一个插件支持的就是 `Python` 中的 `WSGI` 标准, 所以才有了现在的名字.

## 参考资料
- [WSGI tutorial](http://wsgi.tutorial.codepoint.net/intro)
- [An Introduction to the Python Web Server Gateway Interface (WSGI)](http://ivory.idyll.org/articles/wsgi-intro/what-is-wsgi.html)
- [WSGI vs uWSGi with Nginx](https://stackoverflow.com/a/8691337)
- [The uwsgi Protocol](http://uwsgi-docs.readthedocs.io/en/latest/Protocol.html)
- [The uWSGI project](http://uwsgi-docs.readthedocs.io/en/latest/index.html#the-uwsgi-project)
