# encoding:utf-8

"""
分别向顶级域名的权威和DNS递归服务器查询域名的NS记录，并且批量更新
注意：使用两种方法获取域名的NS记录，因为不同方法都无法获取完整的NS记录

"""
# 自身包
import sys

sys.path.append('..')
import random
import datetime
from collections import defaultdict
from multiprocessing import Process, Manager
from multiprocessing import cpu_count  # cpu核数

# 第三方包
import tldextract
import gevent
import gevent.pool
import gevent.monkey
gevent.monkey.patch_all(socket=False, thread=False)  # 务必设置socket/thread，否则报错，因为process和协程同时操作

# 自定义引用
from resolving_domain_dns.resolving_domain_ns_combined import resolving_domain_ns
from public_function.confluent_kakfa_tools import confluent_kafka_producer, confluent_kafka_consumer
from public_function.mysql_db_handle import MySQL
from public_function.Logger import Logger
from public_function.read_config import SystemConfigParse

_system_config = SystemConfigParse('../public_function/system.conf')
_logger = Logger(file_path='../system_running_log/', show_terminal=_system_config.read_log_show())  # 日志配置

domain_dns_rc_set = []  # 协程共享dns结果变量


def average_list(list_temp, n):
    """将列表分为每份为n个值的列表集合"""
    for i in range(0, len(list_temp), n):
        yield list_temp[i:i + n]


def domain_resign_process(domain_data, process_num):
    """根据域名数据的大小和进程数量，进行任务的划分"""
    domain_data_cnt = len(domain_data)
    partition_cnt = domain_data_cnt / process_num + 1
    domain_data_split = list(average_list(domain_data, partition_cnt))
    return domain_data_split


def processing_domain_data(domain_data):
    """
    对要探测的域名数据进行处理，组成可探测的各个部分注意，若是不符合规范的域名，则丢弃
    :param domain_data:  list，要探测的域名数据
    :return:
    processed_domain_data：list，处理后的数据
    """
    processed_domain_data = []
    tld_ns_set = fetch_tld_ns()  # 获取顶级域名的权威地址
    no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=None)
    for domain, old_ns, old_ns_ip in domain_data:
        domain = domain.strip().lower()
        try:
            domain_tld = no_fetch_extract(domain)  # 提取域名各个部分
            tld, reg_domain = domain_tld.suffix, domain_tld.domain
        except Exception, e:
            _logger.logger.error('tldextract失败:' + str(e))
            continue

        # 提取出顶级域名和主域名
        if tld and reg_domain:  # 顶级域名和主域名部分都不为空
            main_domain = reg_domain + '.' + tld  # 完整主域名
            if '.' in tld:  # 顶级域名为两级，则提取出一级顶级域名
                first_tld = tld.split('.')[-1]
                domain_tld = first_tld
            else:
                domain_tld = tld  # 顶级域名只有1级
        elif tld and not reg_domain:  # 顶级域名不为空，主域名为空,例如com.cn
            if '.' in tld:
                domain_tld, main_domain = tld.split('.')[-1], tld
            else:
                _logger.logger.warning('不支持该域名：%s' % domain)
                continue  # 不符合要求

        else:  # 两种情况：1）顶级和主域名部分都为空；2）顶级域名为空，主域名部分不为空(可能为不支持的顶级域名，需要更新tldextract
            _logger.logger.warning('不支持该域名：%s' % domain)
            continue

        tld_ns = tld_ns_set.get(domain_tld)  # 得到顶级域名的权威IP地址
        old_ns_ip_dict = defaultdict(list)
        if tld_ns:
            tld_ns = list(tld_ns)
            random.shuffle(tld_ns)  # 注意：随机
            if old_ns:
                old_ns = old_ns.split(',')  # 将历史ns转换为list
            else:
                old_ns = [] # 否则为空
            for i, ns in enumerate(old_ns):
                if old_ns_ip:
                    old_ns_ip_dict[ns] = old_ns_ip.split(';')[i].split(',')  # 各个ns的IP地址
            processed_domain_data.append([domain, main_domain, domain_tld, tld_ns, old_ns, old_ns_ip_dict])
        else:
            _logger.logger.warning('不支持该顶级域名：%s' % domain_tld)
    return processed_domain_data


def fetch_tld_ns():
    """
    获取顶级域名的权威服务器（ns）IP地址
    """

    tld_ns = defaultdict(set)
    try:
        db_config = _system_config.read_database_config()
        db = MySQL(db_config)
        sql = 'SELECT tld, server_ipv4 from tld_ns_zone'
        db.query(sql)
        tld_ns_query = db.fetch_all_rows()  # 获取已存储的顶级域名的权威服务器信息
        db.close()
    except Exception, e:
        _logger.logger.error("获取顶级域名的权威地址错误：", e)
        return tld_ns

    for i in tld_ns_query:
        tld = str(i['tld'])
        if i['server_ipv4']:
            ipv4 = str(i['server_ipv4']).split(';')
            for ip in ipv4:
                for p in ip.split(','):
                    if p:
                        tld_ns[tld].add(p)
    return tld_ns


def resolving_domain_dns(domain_data):
    """解析域名的DNS记录"""
    global domain_dns_rc_set
    domain, main_domain, tld, tld_ns, old_ns, old_ns_ip = domain_data
    if tld_ns:
        # 获取域名的NS记录
        domain_ns, domain_ns_ip, update_mysql = resolving_domain_ns(main_domain, tld_ns, old_ns, old_ns_ip)
        domain_dns_rc = {
            'domain': domain,
            'NS': ','.join(domain_ns),
            'flag': update_mysql,
            'ns_ip': domain_ns_ip
        }
        domain_dns_rc_set.append(domain_dns_rc)

    else:
        _logger.logger.info('无此域名：%s的顶级域名权威服务器地址' % domain)


def generate_kafka_result(task_id, task_type, task_num, task_total_num, domain_dns_data):
    """
    :param task_id: 任务ID
    :param task_type: 任务类型
    :return:
    producer_dns_result: dict, 域名的dns记录
    """
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # 将列表的数据组成字符串
    domain_dns_items = []
    for rc in domain_dns_data:
        domain_dns_items.append(rc['domain'] + '\t' + 'NS' + '\t' + rc['NS'] + '\t' + str(rc['flag']))
        ns_ip = rc['ns_ip']
        for k in ns_ip:
            domain_dns_items.append(k + '\t' + 'A' + '\t' + ','.join(ns_ip[k]) + '\t' + '0')
    domain_dns_text = '\n'.join(domain_dns_items)  # 成为文本格式
    file_name = current_time + '_' + task_id + '_' + str(task_num) + '_' + str(task_total_num)
    producer_dns_result = {
        'task_id': task_id,
        'file_name': file_name,
        'task_type': task_type,
        'domain_dns': domain_dns_text
    }
    return producer_dns_result


def get_domain_dns_rc(domain_data):
    """
    获取域名的dns记录，并存储到本地或者数据库
    :param domain_data: dict，需要探测的域名数据，包括task_id和domains
    """

    global domain_dns_rc_set  # 存储原始的域名DNS记录数据
    domain_dns_rc_set = []  # 务必置空，因为程序是长期执行的
    task_id = domain_data['task_id']
    domains = domain_data['domains']
    task_type = domain_data['task_type']
    # task_from = domain_data['task_from']  # todo 暂时未使用，是否用于区分任务，从数据库来，还是对方发送
    task_num = domain_data['task_num']
    task_total_num = domain_data['total_task_num']
    domain_ns_data = []  # 存储域名的NS记录
    _logger.logger.info('开始解析任务：%s-%s/%s的域名的NS记录' % (task_id, task_num, task_total_num))
    if domains:  # 探测的域名不为空
        processed_domain_data = processing_domain_data(domains)  # 对探测的域名进行预处理
        domain_split = domain_resign_process(processed_domain_data, cpu_count())  # 进程数量与CPU的核数相同
        process_list = []
        process_manager = Manager()
        process_dns_result = process_manager.dict()

        # 多进程执行域名dns探测
        for i, domains in enumerate(domain_split):
            p = Process(target=coroutine_fetch, args=(domains, i, process_dns_result))
            p.start()
            process_list.append(p)

        # 阻塞进程直到完成
        for p in process_list:
            p.join()
        # 获取各个进程探测的域名ns记录结果
        for i in process_dns_result.values():
            domain_ns_data.extend(i)  # 合并各个进程的域名dns记录

    # 注意，即使域名为空或者结果为空，也要产生响应结果
    dns_result = generate_kafka_result(task_id, task_type, task_num, task_total_num, domain_ns_data)
    kafka_servers = _system_config.read_kafka_servers()
    p = confluent_kafka_producer(topic="dnsrst", servers=kafka_servers, timeout=0)
    p.push(value=dns_result)  # todo，增加是否发送成功
    _logger.logger.info('结束解析任务：%s-%s/%s的域名的DNS记录' % (task_id, task_num, task_total_num))


def coroutine_fetch(domain_data, process_id, process_dns_result):
    """利用协程，批量获取域名的dns记录"""
    coroutine_num = _system_config.read_coroutine_num()
    domain_pool = gevent.pool.Pool(coroutine_num)  # 协程池
    domain_pool.map(resolving_domain_dns, domain_data)
    process_dns_result[process_id] = domain_dns_rc_set


def main():
    # 读取任务队列中的域名数据
    kafka_servers = _system_config.read_kafka_servers()  # kafka地址
    consumer_topic_name = _system_config.read_task_type_topic()  # 消费的任务类型
    msg_content = confluent_kafka_consumer(topic=consumer_topic_name, group=2, servers=kafka_servers, timeout=0).pull()
    while 1:
        try:
            domain_task = msg_content.next()
            domain_data = eval(domain_task[1])
            get_domain_dns_rc(domain_data)
        except Exception, e:
            _logger.logger.error(str(e))
            pass


if __name__ == '__main__':
    main()
