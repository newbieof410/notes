# Docker 指南

> 源文档链接: [Get started with Docker-Part 1](https://docs.docker.com/get-started/)

## Docker 中的概念
Docker 是一个平台, 使开发人员系统管理人员能够使用容器来开发, 部署和运行应用程序. 使用 `Linux` 容器部署应用程序的方式称为容器化. 容器本身并不是新概念, 但是使用容器来方便地部署应用却是之前所没有的.

容器化愈加流行是因为:
- 灵活: 不管多复杂的应用程序都可以实现容器化.
- 轻量: 容器能共享使用主机内核.
- 可交换: 可以在运行中部署更新和升级.
- 可移植: 在本地构建, 到云端部署, 于任何地方使用.
- 可拓展: 可增加并自动分发容器副本.
- 可叠加: 可在运行中垂直地将一个服务叠加在另一个服务之上.

### 镜像和容器
**镜像** 是一个可执行的程序包, 包括了运行一个应用所必需的所有组件: 代码, 运行时, 库, 环境变量和配置文件.

**容器** 是镜像的运行时实例--运行镜像时它在内存中的状态, 即具有状态或用户进程的镜像.

## 容器和虚拟机
容器直接运行在 `Linux` 之上, 与其他容器共享主机内核. 它运行在一个单独的进程中, 不会比非容器化的程序占用更多的内存资源, 这使它很轻量.

相比之下, 虚拟机要运行一个完整的客户机操作系统, 要通过虚拟机管理器实现对主机资源的虚拟化访问. 一般说来, 应用程序并不需要虚拟机环境提供的这么多资源.

<div align="center">
  <table>
    <tbody>
      <tr>
        <td>
          <img src="https://www.docker.com/sites/default/files/Container%402x.png" alt="Container stack example" width="300px"/>
        </td>
        <td>
          <img src="https://www.docker.com/sites/default/files/VM%402x.png" alt="Virtual machine stack example" width="300px"/>
        </td>
      </tr>
    </tbody>
  </table>
</div>
