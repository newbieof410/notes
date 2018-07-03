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

### 简介

客户端与服务器之间的通信数据使用 `RESP` 协议 (REdis Serizlization Protocol) 序列化.

`RESP` 可以表示多种数据类型, 数据类型由第一个字节判断.

数据类型 | 第一个字节 | 规定 | 示例
--- | --- | --- | ---
`Simple String` | `+` | 字符串中不能有回车换行符 | `+OK\r\n`
`Error` | `-` | 与简单字符串类似 | `-Error message\r\n`
`Integer` | `:` | | `:10\r\n`
`Bulk String` | `$` | `$` 后接一个表示字符串长度的数字 | `$6\r\nfoobar\r\n`
`Array` | `*` | `*` 后接表示数组元素个数的数字 | `*0\r\n`

序列化数据的每一部分间使用 `\r\n` 分隔.

另外, 空值可以使用 `Bulk String` 或 `Array` 表示:
- Null Bulk String `$-1\r\n`
- Null Array `*-1\r\n`

`Array` 中的每一项可以是任意的数据类型. 而请求数据虽然要被表示为 `Array`, 但其中的每一项都必须是 `Bulk String`. 响应则没有类型限制.

### 发送请求

现在通过客户端发送一个命令.

```python
redis.set('foo', 'bar')
```

命令 `SET foo bar` 会交由 `Connection` 对象完成序列化: `*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar`.

```python
class Connection(object):

    def pack_command(self, *args):
        "Pack a series of arguments into a value Redis command"
        command = ['$%s\r\n%s\r\n' % (len(enc_value), enc_value)
                   for enc_value in imap(self.encode, args)]
        return '*%s\r\n%s' % (len(command), ''.join(command))
```

在这个方法中, 命令和参数首先会被表示为 `Bulk String`, 然后再组合为 `Array`.

```
SET --> $3\r\nSET\r\n
foo --> $3\r\nfoo\r\n
bar --> $3\r\nbar\r\n
```

### 接收响应

发出请求后使用 `Parser` 对象读取响应. `SET` 执行成功后应该会得到 `+OK\r\n`.

```python
    def read(self, length=None):

        try:
            if length is not None:
                return self._fp.read(length+2)[:-2]
            return self._fp.readline()[:-2]
        except (socket.error, socket.timeout), e:
            raise ConnectionError("Error while reading from socket: %s" % \
                (e.args,))  
```

因为指令由 `\r\n` 分隔, 当没有指定读取字节数时, 可以使用 `readline()` 读取第一行的数据, 当指定了长度时, 则读取相应数量的字节. 然后再丢掉数据末尾的 `\r\n`.

经过处理后会得到 `+OK`.

```python
    def read_response(self):
        response = self.read()
        if not response:
            raise ConnectionError("Socket closed on remote end")

        byte, response = response[0], response[1:]

        # server returned an error
        if byte == '-':
            if response.startswith('ERR '):
                response = response[4:]
                return ResponseError(response)
            if response.startswith('LOADING '):
                # If we're loading the dataset into memory, kill the socket
                # so we re-initialize (and re-SELECT) next time.
                raise ConnectionError("Redis is loading data into memory")
        # single value
        elif byte == '+':
            return response
        # int value
        elif byte == ':':
            return long(response)
        # bulk response
        elif byte == '$':
            length = int(response)
            if length == -1:
                return None
            response = self.read(length)
            return response
        # multi-bulk response
        elif byte == '*':
            length = int(response)
            if length == -1:
                return None
            return [self.read_response() for i in xrange(length)]
        raise InvalidResponse("Protocol Error")
```

这一部分是 `PythonParser` 对响应的解析过程. 首先, 读取一行数据, 拿到第一个字节. 如果类型对应是错误, 简单字符串或整数, 则进行一定的类型转换即可返回. 如果类型是多行字符串, 则再读取字符串长度的字节. 如果是数组, 则要递归上述过程, 将结果以列表的形式返回.

这里直接将 `OK` 返回给上层方法.

## 参考资料
- [redis-py](https://github.com/andymccurdy/redis-py#redis-py)
- [Redis Protocol specification](https://redis.io/topics/protocol)
