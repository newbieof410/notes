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

### Histogram

最后一种 `Histogram` 类型最为复杂, 它会像柱状图一样统计分散在各个区间内的数据个数, 同时也保存了汇总后的值.

下面是一段 `Histogram` 类型采集到的数据, 包括带 `_bucket` 后缀的区间信息, 和与 `Summary` 类型作用类似的数量和总量信息. 在表示区间的数据后, 附带了一个格式如 `{le="xxx"}` 的标签, 代表区间的上限, 其后数据的含义是落在小于等于这个上限的区间内数据的数量. `+Inf` 表示正的无穷大, 那么这个区间对应的值就应该是总的数据个数, 值与 `count` 相等.

```
request_latency_secondes_bucket{le="0.005"} 4.0
request_latency_secondes_bucket{le="0.01"} 7.0
request_latency_secondes_bucket{le="0.025"} 19.0
request_latency_secondes_bucket{le="0.05"} 38.0
request_latency_secondes_bucket{le="0.075"} 69.0
request_latency_secondes_bucket{le="0.1"} 92.0
request_latency_secondes_bucket{le="0.25"} 239.0
request_latency_secondes_bucket{le="0.5"} 457.0
request_latency_secondes_bucket{le="0.75"} 673.0
request_latency_secondes_bucket{le="1.0"} 885.0
request_latency_secondes_bucket{le="2.5"} 886.0
request_latency_secondes_bucket{le="5.0"} 886.0
request_latency_secondes_bucket{le="7.5"} 886.0
request_latency_secondes_bucket{le="10.0"} 886.0
request_latency_secondes_bucket{le="+Inf"} 886.0
request_latency_secondes_count 886.0
request_latency_secondes_sum 434.499202447003
```

`Histogram` 内部维护的数据数量与区间的划分数量有关.

```python
class Histogram(object):

    def __init__(self, name, labelnames, labelvalues, buckets=(.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, _INF)):
        self._sum = _ValueClass(self._type, name, name + '_sum', labelnames, labelvalues)

        ...

        for b in buckets:
            self._buckets.append(_ValueClass(self._type, name, name + '_bucket', bucket_labelnames, labelvalues + (_floatToGoString(b),)))
```

它和 `Summary` 一样, 提供了 `observe` 和 `time` 两个方法用于数据统计, 而 `time` 又是 `observe` 的一个特例, 特别用于统计时间.

```python
    def observe(self, amount):
        '''Observe the given amount.'''
        self._sum.inc(amount)
        for i, bound in enumerate(self._upper_bounds):
            if amount <= bound:
                self._buckets[i].inc(1)
                break
```

给定一个观测值, 总量会增加对应数量, 同时观测值所在区间加一. `Histogram` 中没有维护 `count` 数据, 因为可以使用区间数据间接得到.

## 总结

以上就是客户端提供的四种数据类型了. 如果只看说明文档, 很容易被 `Histogram` 和 `Summary` 的描述搞混淆, 现在至少知道 `Histogram` 中是保存了区间信息的. 另外文档中说到 `Summary` 会实时地计算分位点信息, 这在 Python 客户端中并没有对应的实现.

再来回答开头提到的后两个问题.

**统计方法如何被调用?**

各种类型提供的数据统计方法大概可以分为两类. 第一类的方法如 `inc`, `set`, `observe` 可以用于主动更新数值; 第二类方法如 `time` 可以在经过一个代码块后自动更新数值.

**采集到的样本如何保存?**

从实现中可以看到, 所有的数据更新操作的都是内存中的一份数据, 客户端并不作数据持久化处理. 只有当 Prometheus 主动抓取时, 那一时刻的数据才会被服务端保存下来. 所以数据采集精度是与抓取频率有关的.

还有另一种数据采集的方式会主动保存每一次得到的数据.

最后再补充一点: 在客户端的实现中, 有一个叫做 `REGISTRY` 的对象, 所有实例化的采集器都会在其中注册, 当收到服务器的 `Get` 请求时, 会取出在注册中心注册的所有采集器的值以构造响应.

## 参考资料
- [Prometheus Python Client](https://github.com/prometheus/client_python#prometheus-python-client)
- [proc - process information pseudo-filesystem](http://man7.org/linux/man-pages/man5/proc.5.html)
- [Client metric types](https://prometheus.io/docs/concepts/metric_types/)
