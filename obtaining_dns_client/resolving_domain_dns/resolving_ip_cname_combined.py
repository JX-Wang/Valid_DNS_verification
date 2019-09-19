# encoding:utf-8

"""
结合域名权威服务器和开放递归服务器，获取域名的a和cname记录
@author: cyn
@date: 20190709
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../')

# 系统库函数
import threading
from collections import Counter

# 自定义函数
from resolving_ip_cname_by_ns import query_ip_cname_by_ns
from resolving_ip_cname_by_dns import obtaining_domain_ip
from Logger import Logger
# 全局变量初始化
default_continuous_num = 50  # 默认的探测最少次数
thread_num = 20  # 线程数量
threshold_ip_num = 2  # ip地址出现次数的阈值

logger = Logger(file_path='./query_log/',show_terminal=True)  # 日志配置


class ResultThread(threading.Thread):
    """自定义线程类，用于返回结果"""
    def __init__(self,func,args=()):
        super(ResultThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception,e:
            logger.logger.error('获取线程的结果失败:'+str(e))
            return [], [], 'FALSE'


def obtaining_ip_cname_by_ns(domain, domain_ns):
    """
    向域名权威服务器请求域名的a和cname记录，采用多线程方式，加快探测效率
    :param
    domain:  string，域名
    domain_ns: list，域名的权威服务器域名地址集合
    :return
    domain_ips: list，域名的ip地址集合
    domain_cnames: list, 域名的cname地址集合
    """
    domain_ips = []
    domain_cnames = []

    if not domain_ns:
        logger.logger.warning("该域名:%s不存在的域名权威服务器" % domain)
        return domain_ips, domain_cnames

    sub_thread = []  # 线程列表
    for ns in domain_ns:
        t = ResultThread(query_ip_cname_by_ns, args=(domain, ns))  # 根据域名的权威地址数量，生成相应数量的子线程
        sub_thread.append(t)
        t.setDaemon(True)  # 注意设置其为守护进程
        t.start()

    for t in sub_thread:
        t.join()
        ips, cnames, ip_cname_status = t.get_result()
        if ip_cname_status == 'TRUE':
            domain_ips.extend(ips)
            domain_cnames.extend(cnames)

    return list(set(domain_ips)), list(set(domain_cnames))


def obtaining_ip_cname_by_dns(domain, open_dns):
    """通过开放dns递归服务器获取域名的a和cname记录
    :param domain: string, 域名
    :param open_dns: list, 开放DNS服务器IP地址集合
    """
    dns_unverified_domain_ips = []
    dns_unverified_domain_cnames = []
    dns_ip_cnt = Counter()
    dns_unique_ip_times = []
    is_stop = False  # 是否提前停止探测条件，默认为false
    for i in range(0, len(open_dns), thread_num):
        if is_stop:
            break
        sub_thread = []
        for dns in open_dns[i:i+thread_num]:
            t = ResultThread(obtaining_domain_ip, args=(domain, dns))
            sub_thread.append(t)
            t.setDaemon(True)
            t.start()

        for t in sub_thread:
            t.join(5)  # timeout时间为5s
            ip, cname, status = t.get_result()
            if status == 'TRUE':
                dns_unverified_domain_ips.append(ip)
                dns_unverified_domain_cnames.append(cname)
                for i in ip:
                    dns_ip_cnt[i] += 1
                dns_unique_ip_times.append(len(dns_ip_cnt))
            else:
                dns_unique_ip_times.append(len(dns_ip_cnt)+1)

            # 判断是否提前结束探测任务的条件，连续continuous_num是相同时，则停止继续探测
            continuous_num = len(dns_ip_cnt) * threshold_ip_num  # 最大连续一致的个数
            if len(set(dns_unique_ip_times[-continuous_num:])) == 1 and len(
                    dns_unique_ip_times) >= default_continuous_num:
                is_stop = True

    return dns_unverified_domain_ips, dns_unverified_domain_cnames, dns_ip_cnt


def resolving_domain_ip_cname(domain, domain_ns, open_dns):
    """
    结合顶级域名和域名权威服务器解析域名的NS记录
    :param domain: string, 域名
    :param domain_ns: list, 域名的权威服务器域名地址
    :param open_dns: list, 开放DNS递归服务器的IP地址
    :return
    domain_ips: list, 正确的域名IP地址集合
    domain_cnames: list, 正确的域名cname地址集合
    unknown_domain_ips: list, 未知的域名IP地址集合
    unknown_domain_cnames: list , 未知的域名cname地址集合
    """

    domain_ips = []  # 域名正确的IP地址
    domain_cnames = []  # 域名正确的cname记录
    unknown_domain_ips = []  # 域名未知的ip地址
    unknown_domain_cnames = []  # 域名未知的cname
    # 备注：通过域名权威和开放递归服务器获取域名的ip，未使用多线程，主要是因为权威服务器的时间较短，不影响整体的探测效率
    # 通过域名的权威服务器，获取域名的IP和CNAME
    ns_domain_ips, ns_domain_cnames = obtaining_ip_cname_by_ns(domain, domain_ns)

    # 权威服务器返回的结果为标准有效结果
    domain_ips.extend(ns_domain_ips)
    domain_cnames.extend(ns_domain_cnames)

    if not domain_cnames and domain_ips:  # cname为空和ip不为空，则结束。 若无cname，则表示该域名未使用cdn等技术，ip地址唯一
        return domain_ips, domain_cnames, unknown_domain_ips, unknown_domain_cnames
    if not domain_cnames and not domain_ips: # 都为空，也不再进行探测，保证权威一定有数据返回
        return domain_ips, domain_cnames, unknown_domain_ips, unknown_domain_cnames

    # 利用开放DNS递归服务器获取域名的A和CNAME记录
    dns_unverified_domain_ips, dns_unverified_domain_cnames, dns_ip_cnt = obtaining_ip_cname_by_dns(domain, open_dns)
    # 优化的地方
    if domain_cnames:

        for i, cname in enumerate(dns_unverified_domain_cnames):
            if set(cname) & set(domain_cnames):
                domain_ips.extend(dns_unverified_domain_ips[i])
                domain_cnames.extend(cname)  # 也添加到有效cname中，最后去重
            else:
                intersect = set(domain_ips) & set(dns_unverified_domain_ips[i])
                if intersect:
                    domain_ips.extend(dns_unverified_domain_ips[i])
                else:
                    unknown_domain_ips.extend(dns_unverified_domain_ips[i])
                unknown_domain_cnames.extend(cname)
    else:
        # 超过两个的ip地址，则为正确的IP地址
        for cname in dns_unverified_domain_cnames:  # cname全部添加
            domain_cnames.extend(cname)

        for ip, cnt in dns_ip_cnt.most_common():  # 超过出现次数阈值的IP添加
            if cnt >= threshold_ip_num:
                domain_ips.append(ip)
            else:
                unknown_domain_ips.append(ip)  # 未超过，则为未知ip地址

    return list(set(domain_ips)), list(set(domain_cnames)),list(set(unknown_domain_ips)),list(set(unknown_domain_cnames))


def read_dns():
    dns = []
    fp = open('ODNS.txt', 'r')

    for i in fp.readlines():
        dns.append(i.strip())
    return dns


def main():
    # 测试函数
    domain = 'www.toutiao.com'
    domain = 'www.hitwh.edu.cn'
    domain = 'www.baidu.com'
    open_dns = read_dns()
    domain_ns = ['vip3.alidns.com','vip3.alidns.com']
    domain_ns = ['dns1.hitwh.edu.cn','dns2.hitwh.edu.cn']
    domain_ns = ['dns.baidu.com','ns2.baidu.com']
    r = resolving_domain_ip_cname(domain, domain_ns, open_dns)
    print r
    r[0].sort()
    r[2].sort()
    print r[0]
    print r[2]
    print len(r[0])
    print len(r[2])


if __name__ == '__main__':
    main()