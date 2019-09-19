# coding:utf-8
"""
负责探测任务完成后，向主节点发送信息
"""

from system_parameter import read_server
import requests
TIMEOUT = 30


class TaskConfirm:
    def __init__(self, file_name, domain_ns, task_type,task_id):

        self.post_body = {
            "file_name": file_name,
            'domain_ns': domain_ns,
            'task_id': task_id,
            'task_type': task_type  # query/sec
        }

    def task_confirm(self):
        ip, port = read_server('../system.conf')  # 获取探测节点的地址
        query_url = "http://{ip}:{port}/task_confirm/".format(ip=str(ip), port=str(port))

        try:      
            a = requests.post(url=query_url, json=self.post_body, timeout=TIMEOUT)
        except Exception as e:
            # print "QUERY POST ERROR -> ", str(e)
            return str(e)
        return True


if __name__ == '__main__':
    filename = "000001_20190626173201"
    # TaskConfirm(filename).sec_post()
    # TaskConfirm(filename).query_post()
