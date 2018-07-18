# Python Client

Prometheus 有多种语言实现的客户端库, 可以将我们自定义的监测数据通过 HTTP 提供给外部采集. 这篇笔记首先记录了 Python 客户端的基本使用, 同时也关注了下面几个问题:
1. 客户端中几种监测数据类型的区别
1. 采集到的数据样本如何保存
1. 采集方法如何被调用

## 三步示例

在文档中提供了一个简单示例, 只要三步就能将客户端运行起来.

**ONE 安装客户端**

```Shell
pip install prometheus_client
```

**TWO 运行示例程序**

```Python
import random
import time

from prometheus_client import start_http_server, Summary

# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')


# Decorate function with metric.
@REQUEST_TIME.time()
def process_request(t):
    """A dummy function that takes some time."""
    time.sleep(t)


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8080)
    # Generate some requests.
    while True:
        process_request(random.random())
```

示例中使用了客户端提供的一种数据类型 `Summary`, 它的第一个初始化参数是数据指标的名称, 可用于数据查询.

在 Python 客户端中, `Summary` 类型只提供两类数据:
- count 记录总数, 如调用次数
- size 记录总量, 如总的运行时间

没有提供分位点信息.

**THREE 查看数据**

程序运行起来后, 在地址 [http://localhost:8080/]( http://localhost:8080/) 查看数据. 当然, 若要作为数据抓取目标, 还需要修改 Prometheus 的配置文件.

下面是某一时刻的数据样本.
```shell
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 222732288.0
# HELP process_resident_memory_bytes Resident memory size in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 19951616.0
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 1531725932.76
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 1.78
# HELP process_open_fds Number of open file descriptors.
# TYPE process_open_fds gauge
process_open_fds 6.0
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 1048576.0
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="6",patchlevel="3",version="3.6.3"} 1.0
# HELP request_processing_seconds Time spent processing request
# TYPE request_processing_seconds summary
request_processing_seconds_count 3978.0
request_processing_seconds_sum 1989.6390966859744
```

在最后两行可以看到程序中定义的 `request_processing_seconds` 数据, 其余信息都由客户端默认取得, 包括:
- 当前进程的运行数据
- Python 解释器的基本信息

在 Linux 系统中, 当前进程数据由 `/proc/self/stat` 文件中获得. `proc` 是系统内核以文件形式提供的进程数据接口, 通常挂载在 `/proc`, 它是进程信息的直接来源.

## 数据类型

数据收集客户端主要提供了 4 种类型的监测数据, 包括 Counter, Gauge, Summary 和 Histogram. 目前这几种类型只在客户端有区别, 到了 Prometheus 服务端则按相同的方式处理.

### \_ValueClass
不论是哪种数据类型, 在内部数据都采用了同一种 `_ValueClass` 保存.

在 Python 程序中实现并发通常要创建多个进程, 所以 `_ValueClass` 的实现考虑了单进程和多进程两种情况.

在单进程的情况下, 指标数据被线程间共享, 所以要给数据值加锁.

```python
class _MutexValue(object):
    '''A float protected by a mutex.'''

    _multiprocess = False

    def __init__(self, typ, metric_name, name, labelnames, labelvalues, **kwargs):
        self._value = 0.0
        self._lock = Lock()

    def inc(self, amount):
        with self._lock:
            self._value += amount

    def set(self, value):
        with self._lock:
            self._value = value

    def get(self):
        with self._lock:
            return self._value
```

在多进程的情况下, 每个进程中的采集器都有一个独立的文件用于保存当前进程的数据, 所以获取总体数据就是要将分散的值加在一起. 这部分的程序可以当作多进程交互的一个示例, 不过具体实现比较复杂, 后面只考虑单一进程的情况.

### Counter

`Counter` 是最简单的一种数据类型, 内部只维护着一个 `_value`. 它提供了一个基本方法 `inc` 保证监测的数值只会单调增加.

```python
class Counter(object):

    def __init__(self, name, labelnames, labelvalues):
        self._value = _ValueClass(self._type, name, name, labelnames, labelvalues)

    def inc(self, amount=1):
        if amount < 0:
            raise ValueError('Counters can only be incremented by non-negative amounts.')
        self._value.inc(amount)

    def count_exceptions(self, exception=Exception):
        return _ExceptionCounter(self, exception)
```

另外一个方法 `count_exceptions` 用于对异常计数. 它的使用方式非常灵活: 统计一个函数时可以当作装饰器使用, 而统计一个代码块时则可以用作上下文管理器. 这是因为它定义了对应的特殊方法.

```python
class _ExceptionCounter(object):
    def __init__(self, counter, exception):
        self._counter = counter
        self._exception = exception

    def __enter__(self):
        pass

    def __exit__(self, typ, value, traceback):
        if isinstance(value, self._exception):
            self._counter.inc()

    def __call__(self, f):
        def wrapped(func, *args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return decorate(f, wrapped)
```

作为上下文管理器使用时, 如果内部代码因为异常而退出, `__exit__` 方法会接收到异常的描述信息, 根据描述信息就能判断是否为需要计数的异常了.

### Gauge

`Gauge` 内部也只维护着一个值, 但是这个值既可以增加也可以减少, 可以用来统计数量会上下波动的信息.

它有三个基础方法: `inc`, `dec`, `set`.

此外, 还有一个统计正在处理过程中的函数或代码块数量的方法 `track_inprogress` 和统计运行时间的方法 `time`. 这两个方法也有装饰器和上下文管理器两种使用方式, 实现与上面的 `count_exceptions` 类似. 在后面的两种类型中, 还会见到许多类似的方法.

### Summary

`Summary` 和前面两种类型就不一样了, 它的内部有两个值.

```python
class Summary(object):

    def __init__(self, name, labelnames, labelvalues):
        self._count = _ValueClass(self._type, name, name + '_count', labelnames, labelvalues)
        self._sum = _ValueClass(self._type, name, name + '_sum', labelnames, labelvalues)
```

从示例获得的监测信息中能看到, 它得到了 `指标名称` + `_count`/`_sum` 这两个数据. 它们的含义是什么呢? 来看 `observe` 方法的定义.

```python
    def observe(self, amount):
        '''Observe the given amount.'''
        self._count.inc(1)
        self._sum.inc(amount)
```

每次调用这个方法中, `count` 加一, `sum` 增加指定的数量. 可以知道 `count` 表示的是数量, 而 `sum` 代表总量. 如果还不清楚, 再来看下一个方法 `time`.

```python
    def time(self):

        return _SummaryTimer(self)
```

`time` 用于统计方法或代码块的运行时间, 也有两种使用方式.

```python
class _SummaryTimer(object):
    def __init__(self, summary):
        self._summary = summary

    def __enter__(self):
        self._start = default_timer()

    def __exit__(self, typ, value, traceback):
        # Time can go backwards.
        self._summary.observe(max(default_timer() - self._start, 0))

    def __call__(self, f):
        def wrapped(func, *args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return decorate(f, wrapped)
```

它在内部调用了方法 `observe`, 这时 `count` 就表示进入代码块的次数, 而 `sum` 表示运行的总时间.









## 参考资料
- [Prometheus Python Client](https://github.com/prometheus/client_python#prometheus-python-client)
- [proc - process information pseudo-filesystem](http://man7.org/linux/man-pages/man5/proc.5.html)
- [Client metric types](https://prometheus.io/docs/concepts/metric_types/)
