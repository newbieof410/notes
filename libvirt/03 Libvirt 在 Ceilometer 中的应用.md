# Libvirt 在 Ceilometer 中的应用

我们这里主要学习 `ceilometer.compute.virt.libvirt` 这个包文件, 看看 `ceilometer` 是如何使用 `libvirt` 获取虚拟机运行数据的.

## 管理连接

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

方法 | 返回值 | C API
----- | ------- | -----
virConnect.isAlive | 类型: int <br>含义:1 if alive, 0 if dead | host:<br> virConnectIsAlive
openReadOnly | 类型: virConnect | host:<br> virConnectOpenReadOnly

## 查找 domain

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
        <th>C API</th>
    </tr>
    <tr>
        <td>
            virConnect.lookupByUUIDString
        </td>
        <td>
            类型: virDomain
        </td>
        <td>
            domain:<br>
            virDomainLookupByUUIDString
        </td>
    </tr>
    <tr>
        <td>
            virDomain.info
        </td>
        <td>
            类型: list<br>
            含义:
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
            domain:<br>
            virDomainGetInfo
        </td>
    </tr>
</table>

## 获取网络接口信息

```python
    @libvirt_utils.retry_on_disconnect
    def inspect_vnics(self, instance, duration):
        domain = self._get_domain_not_shut_off_or_raise(instance)

        tree = etree.fromstring(domain.XMLDesc(0))
        for iface in tree.findall('devices/interface'):
            target = iface.find('target')
            if target is not None:
                name = target.get('dev')
            else:
                continue
            mac = iface.find('mac')
            if mac is not None:
                mac_address = mac.get('address')
            else:
                continue
            fref = iface.find('filterref')
            if fref is not None:
                fref = fref.get('filter')

            params = dict((p.get('name').lower(), p.get('value'))
                          for p in iface.findall('filterref/parameter'))
            dom_stats = domain.interfaceStats(name)
            yield virt_inspector.InterfaceStats(name=name,
                                                mac=mac_address,
                                                fref=fref,
                                                parameters=params,
                                                rx_bytes=dom_stats[0],
                                                rx_packets=dom_stats[1],
                                                rx_errors=dom_stats[2],
                                                rx_drop=dom_stats[3],
                                                tx_bytes=dom_stats[4],
                                                tx_packets=dom_stats[5],
                                                tx_errors=dom_stats[6],
                                                tx_drop=dom_stats[7])
```

`domain` 的网络接口设备通过解析 `xml` 文件得到, 使用的解析工具包为 `lxml`.

接口必须具备设备名称和 `mac` 地址, 然后通过设备名称得到接口运行数据.

方法中使用了 `yield` 关键字, 以生成器的方式返回数据. 返回值中包含许多字段, 这里使用了 `namedtuple` 来区分字段含义.

```python
InterfaceStats = collections.namedtuple('InterfaceStats',
                                        ['name', 'mac', 'fref', 'parameters',
                                         'rx_bytes', 'tx_bytes',
                                         'rx_packets', 'tx_packets',
                                         'rx_drop', 'tx_drop',
                                         'rx_errors', 'tx_errors'])
```

下面为本部分用到的 `libvirt` 方法:

<table>
    <tr>
        <th>方法</th>
        <th>返回值</th>
        <th>C API</th>
    </tr>
    <tr>
        <td>
            virDomain.interfaceStats
        </td>
        <td>
            类型: tuple<br>
            含义:
            <ul>
                <li>
                    rx_bytes
                </li>
                <li>
                    rx_packets
                </li>
                <li>
                    rx_errs
                </li>
                <li>
                    rx_drop
                </li>
                <li>
                    tx_bytes
                </li>
                <li>
                    tx_packets
                </li>
                <li>
                    tx_errs
                </li>
                <li>
                    tx_drop
                </li>
            </ul>
        </td>
        <td>
            domain:<br>
            virDomainInterfaceStats
        </td>
    </tr>
    <tr>
        <td>
            virDomain.XMLDesc
        </td>
        <td>
            类型: str<br>
            含义: domain 的 xml 描述
        </td>
        <td>
            domain:<br>
            virDomainGetXMLDesc
        </td>
    </tr>
</table>

## 获取磁盘信息

磁盘信息分为基本配置信息和运行统计信息两部分, 这两部分都需要一个共同的方法来获得磁盘设备.

```python
    def _get_disk_devices(domain):
        tree = etree.fromstring(domain.XMLDesc(0))
        return filter(bool, [target.get("dev") for target in
                             tree.findall('devices/disk/target')
                             if target.getparent().find('source') is not None])
```

设备信息仍然从 `xml` 表示中取得, 并筛选掉了没有设备名称或没有对应镜像文件的条目.

`filter(function, iterable)` 方法会返回一个 `list`, 只包含 `iterable` 中能使 `function` 返回 `true` 的元素.

获取运行统计信息.

```python
    def inspect_disks(self, instance, duration):
        domain = self._get_domain_not_shut_off_or_raise(instance)
        for device in self._get_disk_devices(domain):
            block_stats = domain.blockStats(device)
            block_stats_flags = domain.blockStatsFlags(device, 0)
            yield virt_inspector.DiskStats(
                device=device,
                read_requests=block_stats[0], read_bytes=block_stats[1],
                write_requests=block_stats[2], write_bytes=block_stats[3],
                errors=block_stats[4],
                wr_total_times=block_stats_flags['wr_total_times'],
                rd_total_times=block_stats_flags['rd_total_times'])
```

获取基本配置信息.

```python
    def inspect_disk_info(self, instance, duration):
        domain = self._get_domain_not_shut_off_or_raise(instance)
        for device in self._get_disk_devices(domain):
            block_info = domain.blockInfo(device)
            yield virt_inspector.DiskInfo(device=device,
                                          capacity=block_info[0],
                                          allocation=block_info[1],
                                          physical=block_info[2])
```

新使用的 `libvirt` 方法:

<table>
    <tr>
        <th>方法</th>
        <th>返回值</th>
        <th>C API</th>
    </tr>
    <tr>
        <td>
            virDomain.blockStats
        </td>
        <td>
            类型: tuple<br>
            含义:
            <ul>
                <li>
                    read requests
                </li>
                <li>
                    read bytes
                </li>
                <li>
                    write requests
                </li>
                <li>
                    written bytes
                </li>
                <li>
                    errs
                </li>
            </ul>
        </td>
        <td>
            domain:<br>
            virDomainBlockStats
        </td>
    </tr>
    <tr>
        <td>
            virDomain.blockStatsFlags
        </td>
        <td>
            类型: dict<br>
            含义:
            <ul>
                <li>
                    wr_bytes
                </li>
                <li>
                    wr_operations
                </li>
                <li>
                    rd_bytes
                </li>
                <li>
                    rd_operations
                </li>
                <li>
                    flush_operations
                </li>
                <li>
                    wr_total_times
                </li>
                <li>
                    rd_total_times
                </li>
                <li>
                    flush_total_times
                </li>
            </ul>
        </td>
        <td>
            domain:<br>
            virDomainBlockStatsFlags
        </td>
    </tr>
    <tr>
        <td>
            virDomain.blockInfo
        </td>
        <td>
            类型: list<br>
            含义:
            <ul>
                <li>
                    capacity
                </li>
                <li>
                    allocation
                </li>
                <li>
                    physical
                </li>
            </ul>
        </td>
        <td>
            domain:<br>
            virDomainBlockStatsFlags
        </td>
    </tr>
</table>

## 获取内存和 CPU 信息

内存和 CPU 信息由同一个方法 `inspect_instance` 获取, 我们分开来看.

```python
    def inspect_instance(self, instance, duration=None):
        domain = self._get_domain_not_shut_off_or_raise(instance)

        memory_used = memory_resident = None
        memory_swap_in = memory_swap_out = None
        memory_stats = domain.memoryStats()
        # Stat provided from libvirt is in KB, converting it to MB.
        if 'usable' in memory_stats and 'available' in memory_stats:
            memory_used = (memory_stats['available'] -
                           memory_stats['usable']) / units.Ki
        elif 'available' in memory_stats and 'unused' in memory_stats:
            memory_used = (memory_stats['available'] -
                           memory_stats['unused']) / units.Ki
        if 'rss' in memory_stats:
            memory_resident = memory_stats['rss'] / units.Ki
        if 'swap_in' in memory_stats and 'swap_out' in memory_stats:
            memory_swap_in = memory_stats['swap_in'] / units.Ki
            memory_swap_out = memory_stats['swap_out'] / units.Ki

        ...
```

这里要对内存数据作单位换算, 所以在换算之前要先检查数据存在.

```python
    def inspect_instance(self, instance, duration=None):
        ...

        stats = self.connection.domainListGetStats([domain], 0)[0][1]
        cpu_time = 0
        current_cpus = stats.get('vcpu.current')
        # Iterate over the maximum number of CPUs here, and count the
        # actual number encountered, since the vcpu.x structure can
        # have holes according to
        # https://libvirt.org/git/?p=libvirt.git;a=blob;f=src/libvirt-domain.c
        # virConnectGetAllDomainStats()
        for vcpu in six.moves.range(stats.get('vcpu.maximum', 0)):
            try:
                cpu_time += (stats.get('vcpu.%s.time' % vcpu) +
                             stats.get('vcpu.%s.wait' % vcpu))
                current_cpus -= 1
            except TypeError:
                # pass here, if there are too many holes, the cpu count will
                # not match, so don't need special error handling.
                pass

        if current_cpus:
            # There wasn't enough data, so fall back
            cpu_time = stats.get('cpu.time')

```

首先尝试使用 `vcpu` 的数据之和作为总的 `CPU_time`, 如果数据不足才去使用收集到的 `cpu.time`.

这里用到的 `domainListGetStats` 可以获得 `domain` 的所有数据, 包括网络和磁盘信息, 返回值的结构也很复杂.

用到的 `libvirt` 方法:

<table>
  <tr>
    <th>方法</th>
    <th>返回值</th>
    <th>C API</th>
  </tr>
  <tr>
    <td>
      virDomain.memoryStats
    </td>
    <td>
      类型: dict<br>
      含义:
      <ul>
        <li>
        	swap_in: The total amount of data read from swap space.
        </li>
        <li>
        	swap_out: The total amount of memory written out to swap space.
        </li>
        <li>
        	major_fault: The number of page faults that required disk IO to service.
        </li>
        <li>
        	minor_fault: The number of page faults serviced without disk IO.
        </li>
        <li>
        	unused: The amount of memory which is not being used for any purpose.
        </li>
        <li>
        	actual: Current balloon value.
        </li>
        <li>
        	available: The total amount of memory available to the domain's OS.
        </li>
        <li>
        	usable: How much the balloon can be inflated without pushing the guest system to swap.
        </li>
        <li>
        	rss: Resident Set Size of the process running the domain.
        </li>
        <li>
        	last_update: Timestamp of the last statistic.
        </li>
      </ul>
    </td>
    <td>
      domain:<br>
      virDomainMemoryStats
    </td>
  </tr>
  <tr>
    <td>
      virConnect.domainListGetStats
    </td>
    <td>
      类型: list<br>
      结构: [(virDomain, stats_dict),...]
    </td>
    <td>
      domain:<br>
      virDomainListGetStats
    </td>
  </tr>
</table>
## 参考资料

- [Libvirt Application Development Guide](https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/)
