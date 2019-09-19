# encoding:utf-8
"""
主节点控制功能
"""
import sys
sys.path.append("..")  # 上级目录加入

import tornado.web
import hashlib
import time
import json
import random
from Logger import Logger
from async_http_data import async_fetch
from tornado import gen
from read_config import *
logger = Logger(file_path='./query_log/',show_terminal=True)  # 日志配置
from confluent_kakfa_tools import confluent_kafka_producer
from db_manage.data_base import MySQL
from db_manage.mysql_config import SOURCE_CONFIG_LOCAL as SOURCE_CONFIG
task_size = read_task_size()


def average_list(list_temp, n):
    """将列表平均分为n份"""
    for i in range(0, len(list_temp), n):
        yield list_temp[i:i + n]


def domain_resign_task(domain_data, domain_task_threshold, topic_partition_cnt):
    """根据任务的大小/节点数量/任务消息的最大值，将任务划分为小任务进行分发"""
    domain_data_cnt = len(domain_data)
    if domain_data_cnt <= 1000:  # 小于1000的话，直接返回
        return [domain_data]
    random.shuffle(domain_data)
    if domain_data_cnt / topic_partition_cnt <= domain_task_threshold:
        split_num = domain_data_cnt / topic_partition_cnt + 1
        domain_data_split = list(average_list(domain_data, split_num))  # 将任务进行分隔为5份
    else:
        domain_data_split = list(average_list(domain_data, domain_task_threshold))
    return domain_data_split

class RecvDomainRequestHandler(tornado.web.RequestHandler):
    """
    接收来自对方服务器的域名实时/非实时验证请求
    """
    @gen.coroutine
    def post(self, task_type):
        param = self.request.body.decode('utf-8')
        param = json.loads(param)
        try:
            file_url = param['file_url']
            task_id = param['id']
            request_time = param['time']
            file_md5 = param['file_md5']
        except Exception, e:  # 解析失败
            logger.logger.error('请求内容不符合要求：'+str(e))
            self.write({'time': time.time(), 'code': 2})  # 请求内容不符合要求
            self.finish()
            return

        domain_data = yield async_fetch(file_url, "text")   # 到这里开始不是异步
        if domain_data[0] == "False":
            exception = str(domain_data[1])
            logger.logger.error('获取要探测的域名失败：' + exception)
            self.write({'time': request_time, 'code': 2})  # 获取失败
            self.finish()
            return
        domain_data = domain_data[1]  # 注意
        domain_md5 = hashlib.md5(domain_data.encode("utf-8")).hexdigest()  # 数据自身的md5值

        # 校验数据是否一致
        if domain_md5 == file_md5:
            if task_type in ('sec', 'query'):
                self.write({'time': request_time, 'code': 1})  # 校验一致
                self.finish()
            else:
                logger.logger.error('错误的查询类型：' + str(task_type))
                self.write({'time': request_time, 'code': 2})
                self.finish()
                return
        else:
            logger.logger.error('域名数据校验不一致')
            self.write({'time': request_time, 'code': 2})  # 校验不一致
            self.finish()
            return
        if not domain_data:  # 如果域名为空，则不探测
            return

        domain_data = domain_data.split('\n')
        domain_data = list(set(domain_data))  # 去重复
        domain_data_split = domain_resign_task(domain_data,task_size,5)  # 任务分割
        total_task_num = len(domain_data_split)
        servers = read_confluent_kafka()
        if task_type=='query':
            p = confluent_kafka_producer(topic='query-task', servers=servers, timeout=0)
        else:
            p = confluent_kafka_producer(topic='sec-task', servers=servers, timeout=0)

        for i, domains in enumerate(domain_data_split):
            domain_task = {
                'task_type': task_type,
                'task_id': task_id,
                'domains': domains,
                'task_from': 'bd',   # 数据来自被动方
                'task_num': i+1,  # 任务编号
                'total_task_num': total_task_num  # 任务总共数量
            }
            # 将探测任务发送到任务队列中
            p.push(value=domain_task)
        if task_type == 'sec':
            domains = []
            for i in domain_data:
                domains.append(i.strip())
            save_sec_domains(domains)


def save_sec_domains(domains):
    """将sec的域名存入到数据库中"""
    try:
        db = MySQL(SOURCE_CONFIG)
    except Exception, e:
        logger.logger.error(e)
        return False
    for domain in domains:
        sql = 'insert ignore into focused_domain (domain) values ("%s")' % (domain)
        db.insert_no_commit(sql)
    db.commit()
    db.close()
    return True

