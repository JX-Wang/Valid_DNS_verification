# coding:utf-8
"""
负责探测任务完成后，向主节点发送信息
"""
import sys
sys.path.append('..')

# from system_parameter import read_client
import requests
TIMEOUT = 30

# ip, port = read_client('../system.conf')  # 获取探测节点的地址
ip = 'localhost'
port = '9000'


class TaskConfirm:
    def __init__(self, file_name, task_type,task_id,file_md5):

        self.post_body = {
            'file_name': file_name,
            'task_id': task_id,
            'task_type': task_type,  # query/sec
            'file_md5': file_md5
        }

    def task_confirm(self):

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
