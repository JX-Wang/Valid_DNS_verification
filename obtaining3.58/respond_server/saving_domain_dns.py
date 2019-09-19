# encoding:utf-8

from read_config import *
import time
import os
from Logger import Logger
from confluent_kakfa_tools import confluent_kafka_producer, confluent_kafka_consumer

show_terminal = read_log_show()
logger = Logger(file_path='./query_log/', show_terminal=show_terminal)  # 日志配置
servers = read_confluent_kafka()  # kafka服务器的地址
ip, port = read_http_server()  # 响应web服务器的ip和端口


def monitor_kafka_data():
    """监测数据队列信息"""
    # print servers
    msg_content = confluent_kafka_consumer(topic='dnsrst', group=1, servers=servers, timeout=0).pull()
    # p = confluent_kafka_producer(topic="post-pkg", servers=servers, timeout=1)
    # 变量，记录每个task_id的开始时间以及已接收的完成任务数量，1）若任务完成，向队列发送信息；2）若超过timeout时间，向队列发送。

    while 1:
        try:
            domain_task = msg_content.next()
            domain_result = eval(domain_task[1])
            domain_dns = domain_result['domain_dns']
            file_name = domain_result['file_name']
            task_type = domain_result['task_type']
            task_id = domain_result['task_id']
            # file_md5 = domain_result['file_md5']
            #print domain_result
            #print task_id
            save_domain_data(file_name, domain_dns, task_id, task_type)  # 保存数据

            file_url = "http://{ip}:{port}/file/{file_name}".format(ip=ip, port=str(port),
                                                                    file_name=file_name)  # 文件存储url

            post_body = {
                "id": task_id,
                "time": time.time(),
                "file_url": file_url,
                # "file_md5": file_md5,
                "task_type": task_type
            }

            # p.push(value=post_body)

        except Exception, e:
            # print e
            pass  # 没有next表示broker中没有数据，继续监听即可


def save_domain_data(file_name, domain_dns, task_id, task_type):
    path = './domain_dns_data/' + task_type + '/'
    path = path + task_id + '/'

    folder = os.path.exists(path)

    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
            os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径

    with open(path+file_name, 'w') as fp:
        fp.write(domain_dns)


if __name__ == '__main__':
    monitor_kafka_data()
