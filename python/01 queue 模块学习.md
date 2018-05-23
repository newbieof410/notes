# queue 模块学习
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

下面是用于操作内部的 `queue` 时要用到的 `Lock` 对象, 实现对共享资源的互斥 (mutual exclusion) 访问. 接着是 3 个条件对象.

最后, 还有一个属性用于表示未完成工作的数量.

## deque 对象
在 `Queue` 的内部使用 `deque` 存储数据. `deque` 是双端队列的简称, 在两头都可以进行入队, 出队的操作, 操作的复杂度只有 O(1), 此外, 它还是线程安全的, 并且能高效地利用内存.

虽然 `list` 也能实现类似的功能, 但是它更适合于在数据长度不会经常变化的情况下使用, 像 `pop(0)` 和 `insert(0, v)` 这两个操作, 既要改变列表的长度, 还要逐个移动数据, 所以复杂度为 O(n).

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

### 实际应用
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

`Condition` 是在 `Lock` 之上实现的一种更高级的同步方式. 首先, 使用 `Condition` 操作的也是共享资源, 其次, 在操作时又需要满足一定的条件, 比如队列非空, 队列不满. 操作前需要先获得锁, 如果条件不满足也不会一直占用锁, 而是使用 `wait` 将锁释放, 并进入阻塞状态等待条件满足. 当条件满足时, 需要由另外的线程调用 `notify` 或 `notify_all` 把它们唤醒.

```python
class Condition:

    def __init__(self, lock=None):
        ...
        self._waiters = _deque()

    def _release_save(self):
        self._lock.release()           # No state to save

    def _acquire_restore(self, x):
        self._lock.acquire()           # Ignore saved state

    def _is_owned(self):
        # Return True if lock is owned by current_thread.
        # This method is called only if _lock doesn't have _is_owned().
        if self._lock.acquire(0):
            self._lock.release()
            return False
        else:
            return True

    def wait(self, timeout=None):

        if not self._is_owned():
            raise RuntimeError("cannot wait on un-acquired lock")
        waiter = _allocate_lock()
        waiter.acquire()
        self._waiters.append(waiter)
        saved_state = self._release_save()
        gotit = False
        try:    # restore state no matter what (e.g., KeyboardInterrupt)
            if timeout is None:
                waiter.acquire()
                gotit = True
            else:
                if timeout > 0:
                    gotit = waiter.acquire(True, timeout)
                else:
                    gotit = waiter.acquire(False)
            return gotit
        finally:
            self._acquire_restore(saved_state)
            if not gotit:
                try:
                    self._waiters.remove(waiter)
                except ValueError:
                    pass

    def notify(self, n=1):
        if not self._is_owned():
            raise RuntimeError("cannot notify on un-acquired lock")
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

## put & get
```python
def put(self, item, block=True, timeout=None):

    with self.not_full:
        if self.maxsize > 0:
            if not block:
                if self._qsize() >= self.maxsize:
                    raise Full
            elif timeout is None:
                while self._qsize() >= self.maxsize:
                    self.not_full.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time() + timeout
                while self._qsize() >= self.maxsize:
                    remaining = endtime - time()
                    if remaining <= 0.0:
                        raise Full
                    self.not_full.wait(remaining)
        self._put(item)
        self.unfinished_tasks += 1
        self.not_empty.notify()
```
进入队列前首先要获得锁. 接着判断是否设置了队列的长度, 如果没有限制则直接入队. 如果设置了队列长度, 还要判断入队的等待时间, 默认会一直等待下去.

## join & task_done


## 参考链接
- [What is a mutex?](https://stackoverflow.com/a/34558)
- [deque objects](https://docs.python.org/3.6/library/collections.html#deque-objects)
- [Context Managers](http://docs.python-guide.org/en/latest/writing/structure/#context-managers)
