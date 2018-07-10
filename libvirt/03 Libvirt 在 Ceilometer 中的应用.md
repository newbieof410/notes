# Libvirt 在 Ceilometer 中的应用

我们这里主要学习 `ceilometer.compute.virt.libvirt` 这个包文件, 看看 `ceilometer` 是如何使用 `libvirt` 获取虚拟机运行数据的.

## 获取连接

在所有操作之前, 首先要获得与 `libvirt` 守护进程的连接. 在这个连接中需要指定与哪个虚拟机管理软件进行交互.

```python
class LibvirtInspector(virt_inspector.Inspector):

    def __init__(self, conf):
        super(LibvirtInspector, self).__init__(conf)
        self.connection

    @property
    def connection(self):
        return libvirt_utils.refresh_libvirt_connection(self.conf, self)
```

在初始化方法中, `LibvirtInspector` 调用了基类的初始化方法并建立了一个连接.  `self.connection` 这一句初看起来没有作用, 不过看到下面会发现 `connection` 是用 `@property` 修饰的方法, 使得它能被像属性一样地使用, 所以也可以写为 `self.connection()`.

```python
def refresh_libvirt_connection(conf, klass):
    connection = getattr(klass, '_libvirt_connection', None)
    if not connection or not connection.isAlive():
        connection = new_libvirt_connection(conf)
        setattr(klass, '_libvirt_connection', connection)
    return connection
```

在 `refresh_libvirt_connection` 方法中, 首先会尝试在 `inspector` 对象的 `_libvirt_connection` 属性中获取连接并检查连接是否可用, 只有在没有可用连接时才去创建.

```python
def new_libvirt_connection(conf):
    if not libvirt:
        raise ImportError("python-libvirt module is missing")
    uri = (conf.libvirt_uri or LIBVIRT_PER_TYPE_URIS.get(conf.libvirt_type,
                                                         'qemu:///system'))
    LOG.debug('Connecting to libvirt: %s', uri)
    return libvirt.openReadOnly(uri)
```

创建新连接使用的 `uri` 由配置中获取, 或者根据虚拟机管理器类型使用默认值.

```python
LIBVIRT_PER_TYPE_URIS = dict(uml='uml:///system', xen='xen:///', lxc='lxc:///')
```

然后返回一个只读的连接 `libvirt.openReadOnly(uri)`.

在这一部分使用到的 `libvirt` 方法:

方法 | 返回值 | C API 文档 | C API 方法
----- | ------- | ----- | ---
virConnect.isAlive | 1 if alive, 0 if dead | host | virConnectIsAlive
openReadOnly | virConnect 对象 | host | virConnectOpenReadOnly

## 获取 domain

`domain` 指运行在虚拟机管理器上的虚拟机实例. 这一步要从建立的连接上获取 `domain` 对象.

```python
    def _lookup_by_uuid(self, instance):
        instance_name = util.instance_name(instance)
        try:
            return self.connection.lookupByUUIDString(instance.id)
        except libvirt.libvirtError as ex:
            if libvirt_utils.is_disconnection_exception(ex):
                raise
            msg = _("Error from libvirt while looking up instance "
                    "<name=%(name)s, id=%(id)s>: "
                    "[Error Code %(error_code)s] "
                    "%(ex)s") % {'name': instance_name,
                                 'id': instance.id,
                                 'error_code': ex.get_error_code(),
                                 'ex': ex}
            raise virt_inspector.InstanceNotFoundException(msg)
        except Exception as ex:
            raise virt_inspector.InspectorException(six.text_type(ex))

    def _get_domain_not_shut_off_or_raise(self, instance):
        instance_name = util.instance_name(instance)
        domain = self._lookup_by_uuid(instance)

        state = domain.info()[0]
        if state == libvirt.VIR_DOMAIN_SHUTOFF:
            msg = _('Failed to inspect data of instance '
                    '<name=%(name)s, id=%(id)s>, '
                    'domain state is SHUTOFF.') % {
                'name': instance_name, 'id': instance.id}
            raise virt_inspector.InstanceShutOffException(msg)

        return domain
```

通过 `UUID` 可以获取到 `domain` 对象, 接着检查了 `domain` 的状态, 保证后续的数据获取能正常进行.

在这两个方法中涉及到很多的异常处理, 顺便来看看如何自定义异常.

```python
class InspectorException(Exception):
    def __init__(self, message=None):
        super(InspectorException, self).__init__(message)


class InstanceNotFoundException(InspectorException):
    pass


class InstanceShutOffException(InspectorException):
    pass


class NoDataException(InspectorException):
    pass
```

有 3 个要注意的地方:
1. 继承 `Exception`, 定义自己的异常基类;
1. 在初始化方法中可以传入异常信息;
1. 再衍生出子类来区分异常类型.

在这一部分中用到的 `libvirt` 方法:

<table>
  <tr>
    <th>方法</th>
    <th>返回值</th>
    <th>C API 文档</th>
    <th>C API 方法</th>
  </tr>
  <tr>
    <td>
      virConnect.lookupByUUIDString
    </td>
    <td>
      virDomain
    </td>
    <td>
      domain  
    </td>
    <td>
      virDomainGetInfo  
    </td>
  </tr>
  <tr>
    <td>
      virDomain.info
    </td>
    <td>
    返回值类型为列表, 含义如下:
      <ul>
        <li>
        running state, one of virDomainState
        </li>
        <li>
        maximum memory in KBytes allowed
        <li>
        the memory in KBytes used by the domain
        <li>
        the number of virtual CPUs for the domain
        <li>
        the CPU time used in nanoseconds
      </ul>
    </td>
    <td>
      domain
    </td>
    <td>
      virDomainGetInfo
    </td>
  </tr>
</table>


## 参考资料

- [Libvirt Application Development Guide](https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/)
