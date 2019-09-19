# encoding:utf-8
"""
定时从数据库读取要探测的域名及其历史ns记录发送到任务队列中
"""
import random
import time
import uuid
import sys
sys.path.append("..")  # 导入上级目录

import schedule
from public_function.confluent_kakfa_tools import confluent_kafka_producer
from public_function.mysql_db_handle import MySQL
from public_function.Logger import Logger
from public_function.read_config import SystemConfigParse
_system_config = SystemConfigParse('../public_function/system.conf')
_logger = Logger(file_path='../system_running_log/', show_terminal=_system_config.read_log_show())  # 日志配置


def average_list(list_temp, n):
    """将列表平均分为n份,最后一份可能小于n"""
    for i in range(0, len(list_temp), n):
        yield list_temp[i:i + n]


def domain_resign_task(domain_data, task_domain_size, topic_partition_cnt):
    """根据任务的大小/主题分区数量/任务消息的最大值，将任务划分为小任务进行分发"""
    domain_data_cnt = len(domain_data)
    if domain_data_cnt <= 10000:  # 域名小于10000的话，直接返回数据，即1个任务
        return [domain_data]
    random.shuffle(domain_data)
    if domain_data_cnt / topic_partition_cnt <= task_domain_size:
        split_num = domain_data_cnt / topic_partition_cnt + 1
        domain_data_split = list(average_list(domain_data, split_num))  # 将任务均分到各个分区
    else:
        domain_data_split = list(average_list(domain_data, task_domain_size))  # 将任务按照任务最大域名数量均分
    return domain_data_split


def get_historical_domain_ns():
    """
    从数据库中获取域名的历史ns记录
    """
    try:
        db_config = _system_config.read_database_config()
        db = MySQL(db_config)
        sql = "SELECT domain, ns, ns_ip FROM domain_ns LIMIT 15"
        db.query(sql)
        domain_ns_from_db = db.fetch_all_rows()  # 读取数据库中的ns记录
        db.close()
    except Exception, e:
        _logger.logger.error('从数据库中读取域名的历史ns记录失败：' + str(e))
        return []

    historical_domain_ns = []
    for domain_ns in domain_ns_from_db:
        domain = str(domain_ns['domain']).strip()
        ns = str(domain_ns['ns']).strip()
        ns_ip = str(domain_ns['ns_ip']).strip()
        historical_domain_ns.append((domain, ns, ns_ip))
    return historical_domain_ns


def sending_task_kafka(historical_domain_ns):
    """将要探测的域名历史ns记录发送到任务队列中"""

    if not historical_domain_ns:  # 如果为空，则无需发送任务
        return
    task_domain_size = _system_config.read_task_size()
    topic_partition_cnt = _system_config.read_task_topic_partition_cnt()
    kafka_servers = _system_config.read_kafka_servers()
    sub_ns_tasks = domain_resign_task(historical_domain_ns, task_domain_size, topic_partition_cnt)
    total_num = len(sub_ns_tasks)
    p = confluent_kafka_producer(topic='sec-task', servers=kafka_servers, timeout=0)  # 定时查询
    task_id = str(uuid.uuid1())
    for i, domains in enumerate(sub_ns_tasks):
        domain_task = {
            'task_type': 'sec',
            'task_id': task_id,
            'domains': domains,
            'task_from': 'database',  # 数据来自数据库，与被动方发送的区分
            'task_num': i+1,  # 任务编号
            'total_task_num': total_num  # 任务总共数量
        }

        p.push(value=domain_task)  # 将探测任务发送到任务队列  todo:未有异常判断
    _logger.logger.info('将任务id为:%s的域名集合发送到探测队列中' % task_id)


def creating_domain_ns_task():
    """
    创建定时获取域名ns记录的任务
    """
    historical_domain_ns = get_historical_domain_ns()
    sending_task_kafka(historical_domain_ns)


def starting_periodic_task():
    """定时开始启动探测任务"""
    schedule.every(30).minutes.do(creating_domain_ns_task)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    creating_domain_ns_task()
    # starting_periodic_task()
