# encoding:utf-8

"""
系统服务器启动
"""
import tornado.ioloop
import tornado.httpserver
from tornado.options import define, options
from urls import urls
import tornado.web
from read_config import read_http_server

ip, port = read_http_server()  # 获取主节点的地址
define("port", default=port, help="run on the given port", type=int)
define("bind", default=ip, help="address bind to")


SETTINGS = dict(
    debug=True,  # 调试模式，部署时为false
)


class Application(tornado.web.Application):

    def __init__(self):
        handlers = urls
        settings = SETTINGS
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer( Application(), max_buffer_size=10485760000, max_body_size=10485760000)  # max buffer/body length -> 1G
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":

    main()
