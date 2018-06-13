# 协程 Coroutine

## Coroutine vs. Thread
线程由操作系统的调度程序切换. 多个 `coroutine` 可以运行在同一个线程中, 由程序员或编程语言决定何时切换.

### 关于线程
支持原生线程的语言可以将用户线程放到系统线程, 即内核线程中执行. 每个进程都至少有一个内核线程. 内核线程共享所属进程的内存空间. 进程拥有的资源如内存, 文件句柄, `sockets` 和设备句柄也被其内核线程共享.

系统调度程序是内核的一部分, 管理着线程的执行. 调度程序会给每个线程分配一定执行时间. 在给定时间内即使没有执行完, 调度程序也会打断并切换线程.

在单核设备中, 线程只能在分配的时间片内并发地运行, 但如果设备拥有多个处理器, 不同的线程还能分配到不同的处理器并行地执行.

`Coroutine` 和 `generator` 可用于实现协作式方法. 它们不运行在多个核心线程中被调度程序管理, 而是运行在一个线程中直到交出运行权或者运行结束, 什么时候交出运行权是由程序员控制的.

### 相比线程的优势
`coroutine` 更轻量, 没有调度程序切换所带来的额外开销, 只需要对上下文的切换进行管理.

因为 `coroutine` 的切换由程序员决定, 就能做到比调度程序更精确, 而且还能控制对互斥资源的访问, 从而避免使用锁.

`coroutine` 的内存使用量更小. 多个 `coroutine` 不代表更多的内存占用, 而每个线程都是有自己的栈空间的.

在 `CPython` 中, 因为 `GIL` 的存在, 多线程其实也是像 `coroutine` 一样交替执行的, 但却有等多的额外消耗.

## 示例
定义 `coroutine` 需要使用 `yield` 关键字.
```python
def hello():
   while True:
       x = yield
       print('Hello', x)
```

这个函数看起来很像生成器, 不一样的是 `yield` 位于赋值号右边.

直接调用 `hello` 并不能启动 `coroutine`, 而是会得到生成器对象.
```python
>>> h = hello()
>>> h
<generator object hello at 0x7f11dd5f3fc0>
```

启动要使用 `next()` 函数. 启动后会运行到 `yield` 语句位置停止.
```python
>>> next(h)
```

因为 `yield` 后面没有跟任何表达式, 所以不会有产出值. 但是这里却可以使用 `send()` 方法接收调用方发来的值.
```python
>>> h.send('Monday')
Hello Monday
>>> h.send('world')
Hello world
```

接收到 `send()` 参数后, `h` 会恢复运行, 并再次停止在 `yield` 位置. 最后使用 `close()` 方法终止运行.
```python
>>> h.close()
>>> h.send('world')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
StopIteration
```

## 参考资料
- [What is a coroutine?](https://stackoverflow.com/questions/553704/what-is-a-coroutine)
- [Difference between a “coroutine” and a “thread”?](https://stackoverflow.com/questions/1934715/difference-between-a-coroutine-and-a-thread)
- [Coroutines](http://book.pythontips.com/en/latest/coroutines.html)
- 流畅的 Python
