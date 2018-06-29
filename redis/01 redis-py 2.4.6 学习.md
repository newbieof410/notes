# redis-py 2.4.6 学习

## Connection Pool
客户端在请求 `redis` 服务器的服务时, 由连接池获取连接.

```python
class ConnectionPool(object):
    def __init__(self, connection_class=Connection, max_connections=None,
                 **connection_kwargs):
        self.connection_class = connection_class
        self.connection_kwargs = connection_kwargs
        self.max_connections = max_connections or 2**31
        self._created_connections = 0
        self._available_connections = []
        self._in_use_connections = set()
```
连接池中维护着两个数据结构:
- `_available_connections` 可用连接
- `_in_use_connections` 正在使用的连接

```python
    def get_connection(self, command_name, *keys, **options):
        "Get a connection from the pool"
        try:
            connection = self._available_connections.pop()
        except IndexError:
            connection = self.make_connection()
        self._in_use_connections.add(connection)
        return connection
```
`get_connection` 方法会尝试从 `_available_connections` 中取出可用连接, 如果没有可用连接才去创建新的连接.

所以连接池在刚初始化时是不会立即创建连接的, 直到使用时再去获得第一个连接.

```python
    def make_connection(self):
        "Create a new connection"
        if self._created_connections >= self.max_connections:
            raise ConnectionError("Too many connections")
        self._created_connections += 1
        return self.connection_class(**self.connection_kwargs)
```

连接池使用 `connection_class` 建立连接. 除了默认的 `Connection` 类, 还可以使用自定义的 `Connection` 子类.

```python
    def release(self, connection):
        "Releases the connection back to the pool"
        self._in_use_connections.remove(connection)
        self._available_connections.append(connection)
```

释放连接时, 只是把连接从 `_in_use_connections` 添加到 `_available_connections` 中.

```python
    def disconnect(self):
        "Disconnects all connections in the pool"
        all_conns = chain(self._available_connections, self._in_use_connections)
        for connection in all_conns:
            connection.disconnect()
```

直到调用关闭连接, 才会将保存的连接断开.

## Connection
连接池依赖 `Connection` 或其子类创建连接, 收发数据.

```python
class Connection(object):
    "Manages TCP communication to and from a Redis server"
    def __init__(self, host='localhost', port=6379, db=0, password=None,
                 socket_timeout=None, encoding='utf-8',
                 encoding_errors='strict', parser_class=DefaultParser):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self._sock = None
        self._parser = parser_class()
```
