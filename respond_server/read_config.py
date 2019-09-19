# encoding: utf-8
"""
读取系统配置参数
"""

import ConfigParser

cf = ConfigParser.ConfigParser()
cf.read('system.conf')


def read_http_server():
    """读取http节点信息"""

    ip = cf.get("respond_server", "ip")
    port = cf.getint("respond_server", "port")
    return ip, port


def read_confluent_kafka():
    """读取主节点信息"""

    server_address = cf.get("confluent_kafka_addr","server_address")
    return server_address


def read_log_show():
    """是否将日志在终端显示"""
    show_terminal = cf.getboolean("log_show_terminal","show_terminal")
    return show_terminal


if __name__ == '__main__':
    print read_http_server()
    print read_confluent_kafka()
