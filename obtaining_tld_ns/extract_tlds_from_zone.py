#encoding:utf-8
"""
将root zone文件中的根和顶级域名的权威信息提取出来，然后存入数据库中
"""
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../')

import os
import time
from Logger import Logger
from collections import defaultdict

logger = Logger(file_path='./log/',show_terminal=True)


def is_file_open(filename):
    """判断文件是否打开"""
    p = os.popen("lsof -w %s" % filename)
    # lsof找到打开的文件时有输出
    content = p.read()
    p.close()
    # 通过是否有输出，判断文件是否打开
    return bool(len(content))


def read_root_zone():
    """读取根区文件"""
    file_path = '../tld_ns/root_zone_data/root.zone'

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


def extract_all_tlds():
    """提取root zone文件中的所有顶级域名"""
    logger.logger.info('开始从根区文件中提取顶级域名')
    zone_data = read_root_zone()
    tlds = set()
    for i in zone_data:
        r = i.split('\t')
        tld = r[0][:-1]
        if '.' not in tld and tld:
            tlds.add(tld)
    logger.logger.info('结束从根区文件中提取顶级域名')
    return list(tlds)


if __name__ == '__main__':
    print len(extract_all_tlds())