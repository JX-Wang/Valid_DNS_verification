#coding=utf-8
"""
系统路由设置
"""
from task_handler import RecvDomainRequestHandler

urls = [
    (r"/notify/(\w+)/domain_list", RecvDomainRequestHandler),  # 接收任务请求处理

]
