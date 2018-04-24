# WSGI
> [原文链接 &raquo;](http://wsgi.tutorial.codepoint.net/intro)

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
