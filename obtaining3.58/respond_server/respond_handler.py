# encoding:utf-8
"""
主节点控制功能
"""
import tornado.web
import os
from Logger import Logger
logger = Logger(file_path='./query_log/',show_terminal=True)  # 日志配置
import time
from tornado import gen
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor


class RespDomainResultHandler(tornado.web.RequestHandler):
    """
    根据文件名，服务器返回请求的文件内容
    """
    executor = ThreadPoolExecutor(30)

    @run_on_executor
    def get_domain(self, file_name):
        print 1
	print file_name
	cwd = os.getcwd()
        path = cwd + '/domain_dns_data/sec_compared/' + file_name
        print path
        try:
            fp = open(path, "r")
            data = fp.read()  # 预计不会超过5M
            fp.close()
        except Exception, e:
            print e
            data = ""
        return data

    @gen.coroutine
    def get(self, file_name):
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename=' + file_name)
	print file_name
        data = yield self.get_domain(file_name)
        self.write(data)
        # self.finish()  # 是否需要增加？？？

