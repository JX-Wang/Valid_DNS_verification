# encoding:utf-8
import requests
import random
import sys
sys.path.append('..')

from public_function.Logger import Logger
from public_function.confluent_kakfa_tools import confluent_kafka_consumer
from public_function.read_config import SystemConfigParse

_SYSTEM_CONFIG = SystemConfigParse('../public_function/system.conf')
remote_servers = _SYSTEM_CONFIG.read_remote_multiple_server()
_LOGGER = Logger(file_path='./query_log/', show_terminal=_SYSTEM_CONFIG.read_log_show())  # 日志配置

kafka_servers = _SYSTEM_CONFIG.read_kafka_servers()


def monitor_kafka_data():
    """
    监测kafka响应队列的信息
    """
    msg_content = confluent_kafka_consumer(topic="post-pkg", group=1, servers=kafka_servers, timeout=1).pull()

    while 1:
        try:
            domain_task = msg_content.next()
            domain_result = eval(domain_task[1])
            task_type = domain_result.pop('task_type')
            random.shuffle(remote_servers)

            for remote_ip,remote_port in remote_servers:
                remote_url = "http://{ip}:{port}/notify/{task_type}/result_list".format(ip=remote_ip, port=str(remote_port),
                                                                                   task_type=task_type)  # 远程访问的地址
                send_obj = Send2RemoteHost(remote_url, domain_result)   # 非阻塞异步，只是发送内容
                flag, respond_result = send_obj.send()
                if flag:
                    respond_result = eval(respond_result.text)
                    resp_code = respond_result['code']
                    if resp_code == 1:
                        _LOGGER.logger.info('对方接收域名dns结果文件成功'+remote_ip+':'+str(remote_port))
                        break
                    else:
                        _LOGGER.logger.warning('对方接收域名dns结果文件失败'+remote_ip+':'+str(remote_port))
                else:
                    exception = respond_result
                    _LOGGER.logger.error('向对方发送域名dns结果文件失败:'  + str(exception)+remote_ip+':'+str(remote_port))
        except Exception, e:
            _LOGGER.logger.error('向对方发送域名dns结果失败：'+str(e))
            pass  # 没有next表示broker中没有数据，继续监听即可


class Send2RemoteHost(object):
    """发送内容到主机"""
    def __init__(self, remote_url, dns_data):

        self.post_body = dns_data
        self.remote_url = remote_url

    def send(self):

        try:
            respond = requests.post(url=self.remote_url, json=self.post_body, timeout=60)
        except Exception as e:
            return False, str(e)
        return True, respond


if __name__ == '__main__':
    monitor_kafka_data()
