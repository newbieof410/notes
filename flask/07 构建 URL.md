# 构建 URL

使用 `url_for()` 方法可以生成到指定 `endpoint` 的 `URL`. 由于路由信息保存在应用上下文中, 所以要在具体的上下文中方法才能使用.

如果需要生成外部链接, 除了路由还需要 `host` 地址, 而 `host` 需要从请求上下文中获得. 在 `Flask` 中有 `SERVER_NAME` 配置项, 作用是提供 `host` 信息, 所以如果加了这项配置, 在只有应用上下文时也能生成外部链接.

使用下面的测试程序对几种情况分别研究.

```Python
from flask import Flask, request, url_for

app = Flask(__name__)
app.config.update(
    # SERVER_NAME='127.0.0.2:5001'
)

@app.route('/')
def header():
    rv = ['{}: {}'.format(key, val) for key, val in request.headers.items()]
    return '<br/>'.join(rv)


@app.route('/url')
def url():
    rv = [
        '{}: {}'.format("url_for('url')", url_for('url')),
        '{}: {}'.format("url_for('url', _external=True)", url_for('url', _external=True))
    ]
    return '<br/>'.join(rv)
```

## CASE 1
> 未设置 `SERVER_NAME`, 服务绑定的地址是 `0.0.0.0:5000`.

由 `0.0.0.0`, 回环地址和外网地址都能访问到服务.

生成的外部链接会随请求中使用的 `host` 地址发生变化.

## CASE 2
> 设置了 `SERVER_NAME`, 服务绑定的地址是 `0.0.0.0:5000`.

由 `0.0.0.0`, 回环地址和外网地址都能访问到服务. 如果使用的地址与 `SERVER_NAME` 中的设置不同, 虽然服务器能收到请求, 但应用会无法匹配到正确的路由产生 `404` 错误.

外部链接固定使用 `SERVER_NAME` 作为 `host`.

## CASE 3
> 运行在容器中, 未设置 `SERVER_NAME`, 服务绑定 `0.0.0.0:5000`, 开放容器 `5000` 端口.

与 `CASE 1` 相同, 可访问的地址多了一个容器地址.

外部链接使用的端口号为映射到主机的端口号, 而非在容器中绑定的端口.

## CASE 4
> 运行在容器中, 设置了 `SERVER_NAME`, 服务绑定 `0.0.0.0:5000`, 开放容器 `5000` 端口.

在这种情况下, `SERVER_NAME` 只能设置为容器地址, 每次启动都可能发生变化而且无法从其他设备上访问.

## CASE 5
> 运行在容器中, 未设置 `SERVER_NAME`, 服务绑定 `0.0.0.0:5000`, 开放容器 `5000` 端口, 并设置 Nginx 反向代理.

按照 [文档示例](http://flask.pocoo.org/docs/1.0/deploying/wsgi-standalone/#proxy-setups) 设置代理.
```nginx
server {
    listen 80;

    server_name _;

    access_log  /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log;

    location / {
        proxy_pass         http://app:5000/;
        proxy_redirect     off;

        proxy_set_header   Host                 $host;
        proxy_set_header   X-Real-IP            $remote_addr;
        proxy_set_header   X-Forwarded-For      $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto    $scheme;
    }
}
```
可以生成到代理的外部连接, 但是缺少端口号. 将 `Host` 使用的变量更改为 `$http_host` 后工作正常.

## 总结
生成外部连接时使用的 `host` 信息应该来自于请求头的 `Host` 字段.

如果服务部署在容器中, 虽然访问地址会经过端口映射, 仍然可以生成正确的外部链接.

如果服务部署在代理之后, 请求经过代理时, 需要正确修改请求头信息才能得到预期的外部链接.

## 资料
- [How to get http headers in flask?](https://stackoverflow.com/questions/29386995/how-to-get-http-headers-in-flask)
- [Proxy Setups](http://flask.pocoo.org/docs/1.0/deploying/wsgi-standalone/#proxy-setups)
- [What's the difference of $host and $http_host in Nginx](https://stackoverflow.com/questions/15414810/whats-the-difference-of-host-and-http-host-in-nginx)
- [Nginx server configuration](http://nginx.org/en/docs/http/ngx_http_core_module.html#server)
