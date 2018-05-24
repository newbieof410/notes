# queue 模块学习
`queue` 常被使用在多线程中提供线程安全的数据交换.
## 初始化
```python
class Queue:
    def __init__(self, maxsize=0):
        self.maxsize = maxsize
        self._init(maxsize)
        self.mutex = threading.Lock()
        self.not_empty = threading.Condition(self.mutex)
        self.not_full = threading.Condition(self.mutex)
        self.all_tasks_done = threading.Condition(self.mutex)
        self.unfinished_tasks = 0

    def _init(self, maxsize):
        self.queue = deque()
```
从初始化方法看起, 有一个属性 `maxsize` 表示队列的最大长度, 然后进入到 `_init()` 方法中, 实例化了一个 `deque` 对象. 注意到 `deque` 在初始化时并没有使用 `maxsize`, 说明它的长度可以任意增长, 但是在入队操作时会根据 `maxsize` 进行主动限制.

下面是用于操作内部数据结构 `queue` 时要用到的 `Lock` 对象, 以实现对共享资源的互斥 (mutual exclusion) 访问. 接着有 3 个 `Condition` 对象也起到同样的作用.

最后, `unfinished_tasks` 用于表示未完成工作的数量.

## deque 对象
在 `Queue` 的内部使用 `deque` 存储数据. `deque` 是双端队列的简称, 在两头都可以进行入队, 出队的操作, 操作的复杂度只有 O(1), 此外, 它还是线程安全的, 并且能高效地利用内存.

虽然 `list` 也能实现类似的功能, 但是它更适合于在数据长度不会经常变化的情况下使用, 像 `pop(0)` 和 `insert(0, v)` 这两个操作, 既要改变列表的长度, 还要逐个移动数据, 所以复杂度为 O(n).

### 实际应用
`Queue` 中用来表示队列.
```python
class Queue:
    def _init(self, maxsize):
        self.queue = deque()
```

`Condition` 中用来存储等待的对象 (下面会看到里面的元素其实是处于等待状态的线程的锁).
```python
try:
    from _collections import deque as _deque
except ImportError:
    from collections import deque as _deque

class Condition:

    def __init__(self, lock=None):
        ...
        self._waiters = _deque()
```

## with 语句
`with` 语句用于把一段代码放入上下文管理器 (`context manager`) 所定义的方法中执行. 而上下文管理器是一个对象, 它定义了运行到 `with` 语句时, 需要创建的运行时上下文.

### 上下文管理器可以用在什么地方?
- 操作前一些全局状态需要保存, 操作完成后又要恢复这些状态;
- 访问共享资源前加锁, 退出时释放锁;
- 文件操作前打开文件, 退出时关闭文件.

### 如何实现一个上下方管理器?
第一种方法是使用类实现. 特别地, 在类中需要实现两个方法 `__enter__` 和 `__exit__`, 它们分别负责上下文状态的创建和恢复.
```python
class CustomOpen(object):
    def __init__(self, filename):
        self.file = open(filename)

    def __enter__(self):
        return self.file

    def __exit__(self, ctx_type, ctx_value, ctx_traceback):
        self.file.close()

with CustomOpen('file') as f:
    contents = f.read()
```
在执行到 `with` 语句时, 首先会实例化上下文管理器, 接着调用 `__enter__` 方法, 将它的返回值赋给 `f`. 当 `with` 语句块执行完毕或者执行过程中出现异常, 会调用 `__exit__` 方法恢复环境, 异常的相关信息通过它的参数传入.

第二种方法使用生成器. 当被 `with` 使用时, 它会先执行到 `yield` 把值返回给 `f`. 正常结束, 或遇到异常时, 则会进入 `finally` 完成收尾工作.
```python
from contextlib import contextmanager

@contextmanager
def custom_open(filename):
    file = open(filename)
    try:
        yield file
    finally:
        f.close()

with custom_open('file') as f:
    contents = f.read()
```

### Queue 中的应用
了解了 `with` 的用法, 马上来看一下在实际的模块中它是如何使用的. 在 `Condition` 中, 它的 `__enter__` 和 `__exit__` 直接调用了内部 `Lock` 对象中对应的方法.
```python
class Condition:

    def __init__(self, lock=None):
        if lock is None:
            lock = RLock()
        self._lock = lock
        ...

    def __enter__(self):
        return self._lock.__enter__()

    def __exit__(self, *args):
        return self._lock.__exit__(*args)
```
如果是默认的 `RLock` 对象 (定义在底层的 `_thread.py` 模块中), 它会在 `__enter__` 中加锁, 在 `__exit__` 中开锁.
```python
class RLock(object):

    def __enter__(self, *args, **kwargs): # real signature unknown
        """
        acquire(blocking=True) -> bool

        Lock the lock.
        """
        pass

    def __exit__(self, *args, **kwargs): # real signature unknown
        """
        release()

        Release the lock.
        """
        pass
```

## Lock & Condition
锁原语用于同步, 有锁定和未锁定两种状态. `Lock` 实现了锁原语 (primitive lock), 它提供了两个方法 `acquire` 和 `release`. `acquire` 会尝试获得锁, 即把锁的状态修改为锁定, 但是当锁已经处于锁定状态, 调用 `acquire` 的线程就会被阻塞. `release` 用于释放锁, 把状态改为未锁定, 如果此时还有其他线程等待获取锁, 它们中的一个就会从阻塞状态恢复.

`Condition` 是在 `Lock` 之上实现的一种更高级的同步方式. 首先, 使用 `Condition` 操作的也是共享资源, 所以进入前需要获得锁, 其次, 在操作时可能又需要满足一定的条件, 比如从队列中取数据时, 队列要非空. 一个操作如果获得了锁, 开始执行时却又发现条件不满足, 这时它会使用 `wait` 进入阻塞状态等待条件满足, 并将锁释放. 当条件满足时, 需要由另外的线程调用 `notify` 或 `notify_all` 把它们唤醒.

`Condition` 在初始化时需要一个锁对象, 进入 `Condition` 实际上就是要获得这个锁了. `_waiters` 用来保存谁正在等待条件满足.
```python
class Condition:

    def __init__(self, lock=None):
        if lock is None:
            lock = RLock()
        self._lock = lock
        ...
        self._waiters = _deque()
```

如果一个线程开始执行, 却又发现执行的条件不满足, 那它就需要调用 `wait`, 把自己阻塞在这个函数中, 等待条件满足. 实现阻塞的效果需要另一把锁, 从 `_allocate_lock` 获得. 锁创建后立即使用 `waiter.acquire()` 获得锁, 之后会再次请求锁, 因为锁同时只能被获得一次, 所以这里就会进入阻塞状态. 其实还有一种 `RLock`, 一个线程在释放之前, 可以多次获得锁的使用权, 这里使用的不是这种锁.

在进入阻塞状态前, 线程还要把自己的这把锁放到 `_waiters` 中, 再释放掉大家公用的锁.
```python
    def wait(self, timeout=None):
        ...
        waiter = _allocate_lock()
        waiter.acquire()
        self._waiters.append(waiter)
        saved_state = self._release_save()
        gotit = False
        try:
            if timeout is None:
                waiter.acquire()
            ...
        finally:
            self._acquire_restore(saved_state)
            if not gotit:
                try:
                    self._waiters.remove(waiter)
                except ValueError:
                    pass
```

一个线程进入阻塞状态后, 需要被另一个提供必要条件的线程恢复出来. 这一过程就是把 `_waiters` 中的锁给释放掉.

`all_waiters` 与 `self._waiters` 指向相同的内存空间, 所以 `self._waiters.remove(waiter)` 就相当于 `all_waiters.remove(waiter)`, 当一个线程释放了 `waiter`, 阻塞在 `waite` 中的线程就会进入 `finally`, 把 `remove` 放在 `try...except` 中就避免了重复删除的错误.
```python
    def notify(self, n=1):
        ...
        all_waiters = self._waiters
        waiters_to_notify = _deque(_islice(all_waiters, n))
        if not waiters_to_notify:
            return
        for waiter in waiters_to_notify:
            waiter.release()
            try:
                all_waiters.remove(waiter)
            except ValueError:
                pass
```

### Queue 中的应用
在 `Queue` 中, 所有的操作对象都是内部的 `deque`, 所以, 不同的 `Condition` 使用的也都是同一个锁对象 `mutex`. 条件需要成对存在, 要有依赖条件的一方, 还要有提供条件的一方.

#### task_done & join
这两个方法使用的条件是 `all_tasks_done`.

`task_done` 提供条件. 线程完成队列中的任务时调用.
```python
def task_done(self):
    with self.all_tasks_done:
        unfinished = self.unfinished_tasks - 1
        if unfinished <= 0:
            if unfinished < 0:
                raise ValueError('task_done() called too many times')
            self.all_tasks_done.notify_all()
        self.unfinished_tasks = unfinished
```
`join` 依赖条件. 调用后会等待队列中的任务全部完成.
```python
def join(self):
    with self.all_tasks_done:
        while self.unfinished_tasks:
            self.all_tasks_done.wait()
```
#### put & get
这两个方法比较有趣, 它们相互依赖, 又相互提供条件. 相关的条件是 `not_full`, `not_empty`.

`put` 需要条件 `not_full`, 当队列长度达到了设置的最大值时进入 `wait` 状态. 而入队操作成功后, 又能提供条件 `not_empty`.
```python
def put(self, item, block=True, timeout=None):

    with self.not_full:
        if self.maxsize > 0:
            if not block:
                ...
                while self._qsize() >= self.maxsize:
                    self.not_full.wait()
        ...
        self._put(item)
        self.unfinished_tasks += 1
        self.not_empty.notify()
```

`get` 操作需要条件 `not_empty`, 若执行过程中发现队列为空则进入等待状态, 当操作成功后能提供 `not_full` 的条件.
```Python
def get(self, block=True, timeout=None):

    with self.not_empty:
        if not block:
            ...
            while not self._qsize():
                self.not_empty.wait()
        ...
        item = self._get()
        self.not_full.notify()
        return item
```

## 总结
`queue` 模块建立在 `threading` 模块之上. 在 `Queue` 的实现中, 通过使用 `Lock` 和 `Condition` 实现线程的安全访问. `Condition` 又建立在 `Lock` 之上, 使用 `Condition` 的线程在条件不满足时可以及时释放掉资源的使用权, 避免了死锁的问题; 又能在条件满足时被别的线程唤醒, 而不用自己不断去请求锁, 检查执行条件. 还可以看到, 使用 `Condition` 相当于对不同需求的线程作了分类, 条件满足时这一类线程会被同时唤醒.

此外, 还了解到 `Queue` 内部使用 `deque` 存储数据, 也学到 `with` 应该如何使用.

`queue` 模块完整代码在 [ Lib/queue.py](https://github.com/python/cpython/blob/3.6/Lib/queue.py).

## 参考链接
- [What is a mutex?](https://stackoverflow.com/a/34558)
- [deque objects](https://docs.python.org/3.6/library/collections.html#deque-objects)
- [Context Managers](http://docs.python-guide.org/en/latest/writing/structure/#context-managers)
- [threading — Thread-based parallelism](https://docs.python.org/3.6/library/threading.html)
- [queue — A synchronized queue class](https://docs.python.org/3.6/library/queue.html#module-queue)
