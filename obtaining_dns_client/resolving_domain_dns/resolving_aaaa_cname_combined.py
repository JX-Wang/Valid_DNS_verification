# encoding:utf-8

"""
结合域名权威服务器和开放递归服务器，获取域名的aaaa和cname记录
@author: cyn
@date: 20190709
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../')

import threading
from resolving_aaaa_cname_by_ns import query_aaaa_cname_by_ns
from resolving_aaaa_cname_by_dns import obtaining_domain_aaaa
from Logger import Logger
from collections import Counter

lock = threading.Lock()

default_continuous_num = 50  # 默认的探测最少次数
thread_num = 20  # 线程数量
threshold_aaaa_num = 2  # ip地址出现次数的阈值

logger = Logger(file_path='./query_log/',show_terminal=True)  # 日志配置


class SubThread(threading.Thread):
    """自定义线程类，用于返回结果"""
    def __init__(self,func,args=()):
        super(SubThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception,e:
            logger.logger.error('获取线程的结果失败:'+str(e))
            return [], [] ,'FALSE'


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
    domain_aaaa = []
    domain_cnames = []

    if not domain_ns:
        logger.logger.warning("该域名:%s不存在的域名权威服务器" % domain)
        return domain_aaaa, domain_cnames

    sub_thread = []  # 线程列表
    for ns in domain_ns:
        t = SubThread(query_aaaa_cname_by_ns, args=(domain, ns))  # 根据域名的权威地址数量，生成对应的子线程
        sub_thread.append(t)
        t.setDaemon(True)
        t.start()

    for t in sub_thread:
        t.join()
        aaaa, cnames, ip_cname_status = t.get_result()
        if ip_cname_status == 'TRUE':
            domain_aaaa.extend(aaaa)
            domain_cnames.extend(cnames)

    return list(set(domain_aaaa)), list(set(domain_cnames))


def obtaining_aaaa_cname_by_dns(domain, open_dns):
    """通过开放dns递归服务器获取域名的a和cname记录"""

    dns_unverified_domain_aaaa = []
    dns_unverified_domain_cnames = []
    dns_aaaa_cnt = Counter()
    dns_unique_aaaa_times = []
    is_stop = False
    for i in range(0, len(open_dns), thread_num):
        if is_stop:
            break
        sub_thread = []
        for dns in open_dns[i:i + thread_num]:
            t = SubThread(obtaining_domain_aaaa, args=(domain, dns))
            sub_thread.append(t)
            t.setDaemon(True)
            t.start()

        for t in sub_thread:
            t.join(5)
            aaaa, cname, status = t.get_result()
            if status == 'TRUE':
                dns_unverified_domain_aaaa.append(aaaa)
                dns_unverified_domain_cnames.append(cname)
                for i in aaaa:
                    dns_aaaa_cnt[i] += 1
                dns_unique_aaaa_times.append(len(dns_aaaa_cnt))
            else:
                dns_unique_aaaa_times.append(len(dns_aaaa_cnt) + 1)
                # 用于提前结束探测任务
            continuous_num = len(dns_aaaa_cnt) * threshold_aaaa_num  # 最大连续一致的个数
            if len(set(dns_unique_aaaa_times[-continuous_num:])) == 1 and len(dns_unique_aaaa_times) >= default_continuous_num:
                is_stop = True

    return dns_unverified_domain_aaaa, dns_unverified_domain_cnames, dns_aaaa_cnt




def resolving_domain_aaaa_cname(domain, domain_ns, open_dns):
    """
    结合顶级域名和域名权威服务器解析域名的NS记录
    :param domain: string, 域名
    :param domain_ns: list, 域名的权威服务器域名地址
    :param open_dns: list, 开放DNS递归服务器的IP地址
    :return
    """

    domain_aaaa = []  # 域名正确的IP地址
    domain_cname = []  # 域名正确的cname记录
    unknown_domain_aaaa = []  # 域名未知的ip地址
    unknown_domain_cname = []  # 域名未知的cname
    ns_domain_ips, ns_domain_cnames = obtaining_ip_cname_by_ns(domain, domain_ns)  # 通过域名的权威服务器，获取域名的IP和CNAME

    domain_aaaa.extend(ns_domain_ips)
    domain_cname.extend(ns_domain_cnames)

    if not domain_cname and domain_aaaa:  # cname为空和ip不为空，则结束
        return domain_aaaa, domain_cname, unknown_domain_aaaa, unknown_domain_cname
    if not domain_cname and not domain_aaaa:
        return domain_aaaa, domain_cname, unknown_domain_aaaa, unknown_domain_cname

    dns_unverified_domain_aaaa, dns_unverified_domain_cnames, dns_aaaa_cnt = obtaining_aaaa_cname_by_dns(domain, open_dns)

    if domain_cname:
        for i, cname in enumerate(dns_unverified_domain_cnames):
            if set(cname) & set(domain_cname):
                domain_aaaa.extend(dns_unverified_domain_aaaa[i])
                domain_cname.extend(cname)  # 也添加到有效cname中，最后去重
            else:
                # 可能个别dns不返回cname，只有ip地址
                intersect = set(domain_aaaa) & set(dns_unverified_domain_aaaa[i])
                if intersect:
                    domain_aaaa.extend(dns_unverified_domain_aaaa[i])
                else:
                    unknown_domain_aaaa.extend(dns_unverified_domain_aaaa[i])
                unknown_domain_cname.extend(cname)
    else:
        # 超过两个的ip地址，则为正确的IP地址
        for cname in dns_unverified_domain_cnames:  # cname全部添加
            domain_cname.extend(cname)

        for ip, cnt in dns_aaaa_cnt.most_common():  # 超过出现次数阈值的IP添加
            if cnt >= threshold_aaaa_num:
                domain_aaaa.append(ip)
            else:
                unknown_domain_aaaa.append(ip)  # 未超过，则为未知ip地址

    return list(set(domain_aaaa)), list(set(domain_cname)),list(set(unknown_domain_aaaa)),list(set(unknown_domain_cname))


def read_dns():
    dns = []
    fp = open('ODNS.txt','r')

    for i in fp.readlines():
        dns.append(i.strip())
    return dns



def main():
    domain = 'www.taobao.com'
    open_dns = read_dns()
    domain_ns = ['dns.baidu.com','ns1.baidu.com']
    r = resolving_domain_aaaa_cname(domain, domain_ns, open_dns)
    r[0].sort()
    r[2].sort()
    print r[0]
    print r[2]
    print len(r[0])
    print len(r[2])


if __name__ == '__main__':
    main()