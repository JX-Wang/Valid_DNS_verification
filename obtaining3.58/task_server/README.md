# 获取域名DNS记录--任务节点

## 节点功能介绍
1. 定时将数据库中的域名数据，发送给任务队列，进行探测
2. 负责接收外部发送的域名查询请求，并将其发送给任务队列，进行探测

## 子系统结构

```text
.
├── async_http_data.py             # 异步接收和发送http税局
├── creating_periodic_ns_task.py    # 创建定时的ns查询任务
├── forwarding_remote_host.py        # 转发服务器（该功能待删除）
├── task_handler.py                 # 任务节点web服务器的handler处理函数
├── task_server.py                  # 任务节点web端，用于接收被动方数据（待优化，10月1日）
└── urls.py                          # 路由设置
```

## 运行方法
1. 运行任务任务web服务器，服务器IP地址在配置文件中设置
```text
python task_server.py  
```

2. 运行定时任务
```text
python creating_periodic_ns_task.py
```