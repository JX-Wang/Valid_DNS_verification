# encoding:utf-8

"""
向根域名服务器查询顶级域名的NS权威服务器名称和IP地址
"""

import dns
import dns.name
import dns.query
import dns.resolver
from collections import defaultdict
import random


def get_authoritative_nameserver(tld, nameserver_ips,timeout=3,retry_times=3):
    """
    向根服务器发送解析请求获取顶级域名的NS记录
    :parameter
    tld: str,顶级域名
    nameserver_ips: list,根域名服务器IP地址列表
    timeout: int,超时时间
    retry_times: int ，重试次数
    :returns
    tld_ns: list, 顶级域名的权威名称列表
    ns_a： list, 顶级域名名称对应的IPv4地址
    ns_aaaa: list, 顶级域名名称对应的IPv6地址
    tld_status: str， 获取顶级域名的情况
    """
    tld_ns = []
    a_dict = defaultdict(list)
    aaaa_dict = defaultdict(list)
    success_flag = False
    for i in range(retry_times):
        nameserver_ip = random.choice(nameserver_ips)
        try:
            query = dns.message.make_query(tld, dns.rdatatype.NS,use_edns=True) # 使用edns查询，结果比较多
            response = dns.query.udp(query, nameserver_ip, timeout=timeout)
            success_flag = True
            tld_status = 'TRUE'
            break   # 成功后则停止
        except dns.exception.Timeout as e:
            tld_status = 'TIMEOUT'
        except Exception as e:
            tld_status = e

    if success_flag: # 获取成功
        rcode = response.rcode()
        if rcode != dns.rcode.NOERROR:
            if rcode == dns.rcode.NXDOMAIN:
                tld_status = 'NXDOMAIN'
            else:
                tld_status = dns.rcode.to_text(rcode)
        else:

            # 解析权威section
            if len(response.authority) > 0:
                rr_set =response.authority[0]
                r = str(rr_set.to_text())
                for i in r.split('\n'):
                    i = i.split(' ')
                    rc_type, rc_ttl = i[3], i[1]  # 其实这里应该判断一下，是否是查询的域名的ns
                    if rc_type == 'NS':
                        tld_ns.append((i[4][:-1]).lower())
                tld_ns.sort()
            # 解析additional的section
            if len(response.additional) > 0:
                for i in response.additional:
                    r = str(i.to_text()).split(' ')
                    if r[3] == 'A':
                        a_dict[r[0][:-1]].append(r[4])
                    elif r[3] == 'AAAA':
                        aaaa_dict[r[0][:-1]].append(r[4])

    ns_a = []
    ns_aaaa= []

    for n in tld_ns:
        if a_dict[n]:
            ns_a.append(','.join(a_dict[n]))
        else:
            ns_a.append('')
        if aaaa_dict[n]:
            ns_aaaa.append(','.join(aaaa_dict[n]))
        else:
            ns_aaaa.append('')

    return tld_ns, ns_a, ns_aaaa, tld_status


if __name__ == '__main__':
    tld_ns, ns_a, ns_aaaa, tld_status = get_authoritative_nameserver('ck',['202.12.27.33'])
    print tld_ns
    print ns_a
    print ns_aaaa
    print tld_status