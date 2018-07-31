# Docker SDK
Docker 引擎采用的是非常常见的客户端 / 服务器架构. 既然分成了两部分, 那它们之间就一定有数据通信的需求. 若要通信, 就得考虑如何定义信息格式. 格式定义的方式有很多种, Docker 选择了流行的 REST 风格 API.

REST 并不是什么技术框架, 只不过是一种 API 的设计风格, 而且通常基于 HTTP 使用. 嗯, 好像没什么特别的, 就像一个普通的 Web 服务, 客户端使用 HTTP 发起请求一样. 可是, 通过客户端代码, 还是会发现一些有意思的地方. 下面就从最早的 `0.0.2` 版本看起.

## 初始版本
`0.0.2` 是 `docker-py` 最早的一个标签版本了, 主体就一个文件, 看上去出奇的简单. 选择一部分出来, 就像下面这样.

```python
import requests


class Client(requests.Session):
    def __init__(self, base_url="http://localhost:4243"):
        super(Client, self).__init__()
        self.base_url = base_url

    def _url(self, path):
        return self.base_url + path

    def _result(self, response, json=False):
        if response.status_code != 200:
            response.raise_for_status()
        if json:
            return response.json()
        return response.text

    def containers(self, quiet=False, all=False, trunc=True, latest=False, since=None, before=None, limit=-1):
        params = {
            'limit': 1 if latest else limit,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
            'trunc_cmd': 1 if trunc else 0,
            'since': since,
            'before': before
        }
        u = self._url("/containers/ps")
        return self._result(self.get(u, params=params), True)
```

客户端直接使用 `requests` 库发送 HTTP 请求. 比如现在要获取设备中有哪些容器, 就可以使用 `containers` 方法. 这一步会发送一个 GET 请求, URL 是 [http://localhost:4243/containers/ps](http://localhost:4243/containers/ps). 经过服务端, 也就是 `docker daemon` 处理后, 结果会附加在响应体中发送回来.

很好, 找到了一个 API 接口. 注意到这个接口使用的是 GET 请求, 那我使用浏览器是不是也能得到结果? 打开链接就会发现, 根本没有服务器在服务这个地址.

事实上, 现在的 Docker 服务端已经更改了接口地址, `0.0.2` 版本的客户端也不再能使用, 不过可以明白的一点是 Docker 客户端与服务端本质上是通过基于 HTTP 的 REST 接口交互的, 客户端既可以是安装后自带的命令行程序, 也可以是各种语言中的 SDK.
