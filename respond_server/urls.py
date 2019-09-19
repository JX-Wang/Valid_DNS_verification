#coding=utf-8
"""
系统路由设置
"""
from respond_handler import RespDomainResultHandler

urls = [
    (r'/file/([\w-]+)', RespDomainResultHandler),  # 全量任务完成响应
    (r'/update/([\w-]+)', RespDomainResultHandler),  # 全量任务完成响应

]
