#encoding:utf-8
"""
将root zone文件中的根和顶级域名的权威信息提取出来，然后存入数据库中
"""
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./')

import os
import time
from collections import defaultdict
from extract_tlds_from_zone import extract_all_tlds
from download_root_zone import root_zone_download
from Logger import Logger

logger = Logger(file_path='./log',show_terminal=True)


def is_file_open(filename):
    """判断文件是否打开"""
    p = os.popen("lsof -w %s" % filename)
    # lsof找到打开的文件时有输出
    content = p.read()
    p.close()
    # 通过是否有输出，判断文件是否打开
    return bool(len(content))


def get_tld_ns_ip(tlds,zone_data):
    """
    处理从root.zone得到的数据，以tld为key构建字典，并通过字典的key值检索将相关联的数据整理出来
    """
    tld_data = []
    tld_result =[]
    for i in zone_data:
        a = i.split('\t')  # 去除换行符
        b = [x.strip() for x in a if x.strip() != '']  # 去除空字符
        b[0] = b[0][:-1]    # 去除顶级域名最后的点
        tld_data.append(b)  # 按行记录到tld_data中
    data_ns = defaultdict(list)
    data_ipv4 = defaultdict(list)
    data_ipv6 = defaultdict(list)
    # 构建三个字典，分别存储NS,A,AAAA记录
    for data in tld_data:
        if data[3] == 'NS':
            data[4] = data[4][:-1]
            data_ns.setdefault(data[0], []).append(data[4])
        elif data[3] == 'A':
            data_ipv4.setdefault(data[0], []).append(data[4])
        elif data[3] == 'AAAA':
            data_ipv6.setdefault(data[0], []).append(data[4])
    # 先得到tld的ns记录列表，以ns记录为key值检索A和AAAA字典，得到相应数据
    for tld in tlds:
        ns_list = list(data_ns[tld])
        # ns_str = ';'.join(ns_list)
        ipv4_list = []
        ipv6_list = []
        for ns in ns_list:
            ipv4 = list(data_ipv4[ns])
            ipv4 = ';'.join(ipv4)
            ipv4_list.append(ipv4)
        for ns in ns_list:
            ipv6 = list(data_ipv6[ns])
            ipv6 = ';'.join(ipv6)
            ipv6_list.append(ipv6)
        # ipv4_str = ';'.join(ipv4_list)
        # ipv6_str = ';'.join(ipv6_list)
        tld_result.append((tld, ns_list, ipv4_list, ipv6_list))
    return tld_result


def get_root(is_integrity=False):
    zone_data = read_root_zone()
    if len(zone_data) <= 21000:  # 根据完整的zone的大小，如果小于某阈值，则判断其不完整
        logger.logger.warning('Root Zone文件较小，请检查是否完整后，重新运行')
        if not is_integrity:  # 若完整，则运行
            return
    tld_data = []
    for i in zone_data:
        a = i.split('\t')  # 去除换行符
        b = [x.strip() for x in a if x.strip() != '']  # 去除空字符
        tld_data.append(b)  # 按行记录到tld_data中
    data_ns = defaultdict(list)
    data_ipv4 = defaultdict(list)
    data_ipv6 = defaultdict(list)
    # 构建三个字典，分别存储NS,A,AAAA记录
    for data in tld_data:
        if data[3] == 'NS':
            data_ns.setdefault(data[0], []).append(data[4])
        elif data[3] == 'A':
            data_ipv4.setdefault(data[0], []).append(data[4])
        elif data[3] == 'AAAA':
            data_ipv6.setdefault(data[0], []).append(data[4])
    ns_list = list(data_ns['.'])
    ns_list1 = []
    ipv4_list = []
    ipv6_list = []
    for ns in ns_list:
        ipv4 = list(data_ipv4[ns])
        ipv4 = ';'.join(ipv4)
        ipv4_list.append(ipv4)
        ipv6 = list(data_ipv6[ns])
        ipv6 = ';'.join(ipv6)
        ipv6_list.append(ipv6)
    for ns in ns_list:
        temp = ns[:-1]
        ns_list1.append(temp)
    return ns_list1,ipv4_list,ipv6_list


def read_root_zone():
    """读取根区文件"""
    file_path = './root_zone_data/root.zone'

    while 1:  # 判断文件是否处于打开状态
        if is_file_open(file_path):
            # sys.stdout.write("\r文件处于编辑状态，等待文件完成编辑中...")
            logger.logger.warning('文件处于编辑状态，等待文件完成编辑中...')
            # sys.stdout.flush()
            time.sleep(10)
        else:
            break
    try:
        fp = open(file_path, 'r')
    except Exception as e:
        logger.logger.error(e)
        return []
    zone_data = fp.readlines()
    fp.close()
    return zone_data


def get_tld_ns_by_zone(is_integrity=False):
    """获取指定顶级域名的权威和IP地址"""

    logger.logger.info('开始从根区文件中提取根和顶级域名的权威信息')
    root_zone_download()
    zone_data = read_root_zone()
    tld_result = []
    if len(zone_data) <= 21000: # 根据完整的zone的大小，如果小于某阈值，则判断其不完整
        logger.logger.warning('Root Zone文件较小，请检查是否完整后，重新运行')
        if not is_integrity:  # 若完整，则运行
            return
    # 从根区文件中获取顶级域名的权威信息
    tlds = extract_all_tlds()
    tld_result = get_tld_ns_ip(tlds, zone_data)
    logger.logger.info('结束从根区文件中提取根和顶级域名的权威信息')
    return tld_result


if __name__ == '__main__':
    get_root()