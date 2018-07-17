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

在多进程的情况下, 不同进程中采集到的数据会保存到各自的文件中, 再汇总得到总数据.






## 参考资料
- [Prometheus Python Client](https://github.com/prometheus/client_python#prometheus-python-client)
- [proc - process information pseudo-filesystem](http://man7.org/linux/man-pages/man5/proc.5.html)
- [Client metric types](https://prometheus.io/docs/concepts/metric_types/)
