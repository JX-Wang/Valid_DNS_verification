#encoding:utf-8
"""
向域名的权威域名服务器查询域名的MX记录
"""
import random
import dns.query
import dns.resolver
from is_legal_ip import judge_legal_ip
from resolving_ip_cname_by_dns import obtaining_domain_ip


def query_mx_by_ns (domain, authoritative_ns, local_dns ='1.2.4.8', timeout=2, retry_time=2):
    """
    向域名的NS权威服务器查询域名的IP记录，若有CNAME，则获取CNAME的记录
    domain: 要查询的域名，注意为全域名
    authoritative_ns: 域名的权威服务器地址，可能为域名或IP
    timeout:超时时间
    retry_time：重试次数
    """

    domain_mx = []
    status = 'FALSE'

    if not judge_legal_ip(authoritative_ns):  # 若为域名，则先解析出来权威服务器的IP
        authoritative_ip, _, auth_ip_cname_status = obtaining_domain_ip(authoritative_ns, local_dns)
        if auth_ip_cname_status != "TRUE":
            return domain_mx, status
    else:
        authoritative_ip = [authoritative_ns]

    query = dns.message.make_query(domain, dns.rdatatype.MX,use_edns=True)
    for _ in range(retry_time): # 重试次数
        try:
            authoritative_ns = random.choice(authoritative_ip)  # 随机选择一个IP地址
            response = dns.query.udp(query, authoritative_ns, timeout=timeout)
            for rrset in response.answer:
                r = str(rrset.to_text())
                for i in r.split('\n'):  # 注意
                    i = i.split(' ')
                    rc_type = i[3]
                    if rc_type == 'MX':
                        domain_mx.append(' '.join(i[4:])[:-1])
            status = 'TRUE'
            break
        except dns.resolver.NoAnswer:
            status = 'NO ANSWERS'
        except dns.resolver.NXDOMAIN:
            status = "NXDOMAIN"  # 只执行一次
            break
        except dns.resolver.NoNameservers:
            status = 'NO NAMESERVERS'
        except dns.resolver.Timeout:
            status = 'TIMEOUT'
        except:
            status = 'UNEXPECTED ERRORS'

    return domain_mx, status


def resolving_domain_mx(main_domain, domain_ns):
    """

    :param main_domain: string, 主域名
    :param domain_ns: list，域名权威服务器域名地址
    :return:
    domain_soa: string ,域名的soa记录
    """
    for ns in domain_ns:
        domain_soa, status = query_mx_by_ns(main_domain, ns)
        if status == 'TRUE':
            return domain_soa

    return []


if __name__ == '__main__':

    # print resolving_domain_soa ('baidu.com', ['202.108.22.220'])
    print resolving_domain_mx ('baidu.com', ['ns3.baidu.com', 'ns2.baidu.com'])
    # print resolving_domain_soa ('hao123.com', ['dns.baidu.com'])
    print resolving_domain_mx ('hitwh.edu.cn', ['dns2.hitwh.edu.cn'])
