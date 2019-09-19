# encoding:utf-8
"""
结合顶级域名和域名的权威服务器，获取域名的ns记录，获取逻辑详见开发文档
@author: 程亚楠
"""

import random
from resolving_domain_ns_by_tld import get_domain_ns_hierarchical_dns # 获取域名dns
from resolving_domain_ns_by_ns import query_domain_ns_by_ns  # 获取域名dns
from resolving_domain_ns_by_dns import obtaining_domain_ns_name
from collections import defaultdict
from resolving_ip_cname_by_dns import obtaining_domain_ip


def resolving_domain_ns_by_tld(main_domain, tld_ns_ip):
    """
    向顶级域名权威服务器请求域名的NS记录
    :param main_domain:  string，主域名
    :param tld_ns: list，域名对应的顶级域名的权威服务器ip地址集合
    :return
        ns_by_tld: list，通过顶级域名权威获取的域名的ns名称
        ns_ip_by_tld: dict, 通过顶级域名权威获取的域名的ns的IP地址
    """
    ns_by_tld = []
    ns_ip_by_tld = {}
    if not tld_ns_ip:
        return ns_by_tld, ns_ip_by_tld
    for ip in tld_ns_ip:
        ns_result, ns_status = get_domain_ns_hierarchical_dns(main_domain, True, tld_server=ip)  # 向根节点--》顶级权威获取域名的权威地址
        if ns_status == 'TRUE':  # 获取成功则停止
            ns_by_tld.extend(ns_result[0])  # 可能为空
            ns_ip_by_tld = ns_result[1]
            break
        elif ns_status == 'TIMEOUT':  # 若TIMEOUT，继续探测
            continue
        else:
            break  # 停止探测

    return list(set(ns_by_tld)), ns_ip_by_tld


def resolving_domain_ns_by_ns(main_domain, tld_domain_ns, tld_domain_ns_ip=None):
    """
    向域名的权威服务器请求ns，获取域名权威服务器上的的ns记录集合
    :param string domain: 要解析的原始域名
    :param string main_domain: 主域名
    :param list tld_domain_ns: tld解析的域名的ns权威服务器地址名称集合
    :return list domain_ns: 经过验证后的有效域名ns地址集合
    """

    if tld_domain_ns_ip is None:
        tld_domain_ns_ip = {}
    ns_domain_ns = []
    ns_domain_ns_ip = defaultdict(list)
    random.shuffle(tld_domain_ns)  # 随机
    ns_status = 'FALSE'
    for ns in tld_domain_ns:
        ip = tld_domain_ns_ip.get(ns)
        ns_ns, ns_ns_ip, ns_status, _ = query_domain_ns_by_ns(main_domain, ns, ip)
        if ns_status == 'TRUE':
            ns_domain_ns.extend(ns_ns)
            ns_domain_ns_ip = ns_ns_ip
            break
        elif ns_status == 'TIMEOUT':
            continue
        else:
            break
    
    if ns_status == 'TRUE':
        return list(set(ns_domain_ns)), ns_domain_ns_ip
    else:
        ns_domain_ns, ns_domain_ns_ip, ns_status = obtaining_domain_ns_name(main_domain)
        return ns_domain_ns, ns_domain_ns_ip
        
def get_last_ns_ip(domain_ns, ns_by_tld_ip, ns_by_ns_ip, old_ns_ip):
    domain_ns_ip = defaultdict(list)
    for ns in domain_ns:
        ns_ip = ns_by_ns_ip.get(ns)
        tld_ip = ns_by_tld_ip.get(ns)
        old_ip = old_ns_ip.get(ns)
        if ns_ip:
            last_ip = ns_ip
        else:
            if tld_ip:
                last_ip = tld_ip
            else:
                if old_ip:
                    last_ip = old_ip
                else:
                    ip,_, _ = obtaining_domain_ip(ns)  # 在线获取
                    last_ip = ip

        domain_ns_ip[ns] = last_ip
    return domain_ns_ip


def resolving_domain_ns(main_domain, tld_ns_ip, old_ns, old_ns_ip):
    """
    结合顶级域名和域名权威服务器解析域名的NS记录
    :param main_domain: string, 域名对应的主域名
    :param tld_ns_ip: list, 域名的顶级域名对应的权威服务器IP地址集合
    :param old_ns: list, 域名原有的ns地址
    :param old_ns_ip: defaultdict, 域名的ns地址的ip地址
    :return:
        domain_ns, list, 域名的ns域名集合
        domain_ns_ip, defaultdict, 域名的ns名称的ip地址
        update_mysql，是否需要更新mysql的标记位，0：不更新；1：更新
    """
    ns_by_tld, ns_by_tld_ip = resolving_domain_ns_by_tld(main_domain, tld_ns_ip)   # 通过顶级域名权威获取域名的ns
    ns_by_ns_ip = defaultdict(list)
    if ns_by_tld:  # 顶级域名权威服务器返回域名ns记录不为空
        ns_by_ns, ns_by_ns_ip = resolving_domain_ns_by_ns(main_domain, ns_by_tld, ns_by_tld_ip)  # 通过域名的权威服务器获取权威ns地址
        # print main_domain,"顶级权威结果：",ns_by_tld, "授权权威结果：", ns_by_ns  # 用于测试顶级和授权权威的信息
        ns_by_ns.sort()
        old_ns.sort()
        if ns_by_ns:  # 不为空
            if old_ns:
                if ns_by_ns == old_ns:  # 完全相同，使用最新数据，不更新数据库
                    domain_ns = ns_by_ns
                    update_mysql = 0
                 
                else:
                    intersection_ns = list(set(ns_by_ns).intersection(set(old_ns)))
                    if intersection_ns:  # 有交集，则结果为最新记录，更新数据库
                        domain_ns = ns_by_ns
                        update_mysql = 1
                    else:
                        next_old_ns = resolving_domain_ns_by_ns(main_domain, old_ns)
                        if next_old_ns:
                            domain_ns = old_ns
                            update_mysql = 0
                        else:
                            domain_ns = ns_by_ns
                            update_mysql = 1
            else:
                domain_ns = ns_by_ns  # 若旧数据为空，新数据不为空，则使用新数据
                update_mysql = 1

        else:  # 最新授权权威为空
            if old_ns:
                next_old_ns = resolving_domain_ns_by_ns(main_domain, old_ns)
                if next_old_ns:
                    domain_ns = old_ns
                    update_mysql = 0
                else:
                    domain_ns = []
                    update_mysql = 1
            else:
                domain_ns = []
                update_mysql = 0
    else:
       # print main_domain, "顶级域名为空"
        if old_ns:
            next_old_ns = resolving_domain_ns_by_ns(main_domain, old_ns)
            if next_old_ns:
                domain_ns = old_ns
                update_mysql = 0
            else:
                domain_ns = []
                update_mysql = 1
        else:
            domain_ns = []
            update_mysql = 0
    domain_ns_ip = get_last_ns_ip(domain_ns,ns_by_tld_ip, ns_by_ns_ip, old_ns_ip)
    return domain_ns, domain_ns_ip, update_mysql


def main():
    main_domain = 'baidu.com'
    tld_ns = ['192.5.6.30','192.33.14.30']
    print resolving_domain_ns(main_domain, tld_ns, [], {})


if __name__ == '__main__':
    main()
