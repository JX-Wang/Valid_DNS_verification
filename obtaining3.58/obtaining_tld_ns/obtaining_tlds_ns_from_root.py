# encoding:utf-8
"""
通过向root请求得到根和顶级域名的权威信息，然后存入数据库中
"""
from extract_tlds_from_root import get_authoritative_nameserver
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../')

import gevent  # 第三方库，通过greenlet实现协程
import gevent.pool
from multiprocessing import Process, Manager
from Logger import Logger
from extract_tlds_from_zone import extract_all_tlds


logger = Logger(file_path='./log',show_terminal=True)
tld_result = []


def average_list(list_temp, n):
    """将列表分为每份为n个值的列表集合"""
    for i in range(0, len(list_temp), n):
        yield list_temp[i:i + n]


def tld_resign_process(tlds, process_num):
    """根据数据的大小和进程数量，进行任务的划分"""
    domain_data_cnt = len(tlds)  # cnt是count的缩写，domian_data_cnt 意思就是域名数据的数量
    partition_cnt = domain_data_cnt / process_num + 1   # 应该分配的每个分区域名数据的数量
    domain_data_split = list(average_list(tlds, partition_cnt))  # 返回的是列表的列表，即[[],[],[]]的形式，用来保存域名数据
    return domain_data_split


def coroutine_fetch(tlds,process_dns_result,coroutine_num):
    """利用协程，批量向根域名服务器请求数据"""
    tld_pool = gevent.pool.Pool(coroutine_num)  # 协程池
    tld_pool.map(get_tld_ns_by_root, tlds)
    for i in tld_result:
        process_dns_result.append(i)


def get_tld_ns_by_root(tld):
    # """获取指定顶级域名的权威和IP地址"""
    global tld_result
    tld_ns, ns_a, ns_aaaa, tld_status = get_authoritative_nameserver(tld,['202.12.27.33'])
    tld_ns = ';'.join(tld_ns)
    ns_a = ';'.join(ns_a)
    ns_aaaa = ';'.join(ns_aaaa)
    tld_result.append((tld,tld_ns,ns_a,ns_aaaa))


def extract_ns_ip_by_root():
    global tld_result
    tld_result = []
    logger.logger.info('开始从根域名服务器中提取顶级域名的权威信息')
    tlds = extract_all_tlds()
    process_list = []
    tld_split = tld_resign_process(tlds, 4)   # 开四个进程
    process_manager = Manager()
    process_dns_result = process_manager.list()
    for i, tld in enumerate(tld_split):
        p = Process(target = coroutine_fetch, args = (tld,process_dns_result, 300))  # 开300协程
        p.start()
        process_list.append(p)

    # 阻塞进程直到完成
    for p in process_list:
        p.join()
    logger.logger.info('结束从根域名服务器中提取顶级域名的权威信息')
    return process_dns_result


if __name__ == '__main__':
    extract_ns_ip_by_root()