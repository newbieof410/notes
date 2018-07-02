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

`Connection` 使用 `TCP` 连接服务器.
```python
    def connect(self):
        "Connects to the Redis server if not already connected"
        if self._sock:
            return
        try:
            sock = self._connect()
        except socket.error, e:
            raise ConnectionError(self._error_message(e))

        self._sock = sock
        self.on_connect()

    def _connect(self):
        "Create a TCP socket connection"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.socket_timeout)
        sock.connect((self.host, self.port))
        return sock
```

连接创建成功后要执行 `on_connect()` 方法, 进行密码认证和数据库选择.

```python
    def on_connect(self):
        "Initialize the connection, authenticate and select a database"
      self._parser.on_connect(self)

      # if a password is specified, authenticate
      if self.password:
          self.send_command('AUTH', self.password)
          if self.read_response() != 'OK':
              raise ConnectionError('Invalid Password')

      # if a database is specified, switch to it
      if self.db:
          self.send_command('SELECT', self.db)
          if self.read_response() != 'OK':
              raise ConnectionError('Invalid Database')
```

同一个客户端对象可以安全地使用在多个线程中, 因为客户端不提供会改变自身状态的操作. 所以在这里设置数据库后就不能修改了.

服务端发来的消息会交给 `Parser` 对象解析, 需要把 `socket` 连接提供过去.

## Parser

`Parser` 类用于解析服务端返回的数据.

这里有两个 `Parser` 实现:
- `PythonParser` 由 `Python` 实现;
- `HiredisParser` 由 `C` 实现, 提供了到 `Python` 的绑定, 需要额外安装 `hiredis` 包.

客户端会优先使用速度更快的 `HiredisParser`.
```python
try:
    import hiredis
    DefaultParser = HiredisParser
except ImportError:
    DefaultParser = PythonParser
```

## RESP
现在通过客户端发送一个命令.

```python
redis.set('foo', 'bar')
```

命令 `SET foo bar` 在 `Connection` 对象中会先被序列化为 `*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar` 再发出.

```python
class Connection(object):

    def pack_command(self, *args):
        "Pack a series of arguments into a value Redis command"
        command = ['$%s\r\n%s\r\n' % (len(enc_value), enc_value)
                   for enc_value in imap(self.encode, args)]
        return '*%s\r\n%s' % (len(command), ''.join(command))
```
