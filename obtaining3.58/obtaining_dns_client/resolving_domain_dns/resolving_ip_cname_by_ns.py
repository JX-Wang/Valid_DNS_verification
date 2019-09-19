#encoding:utf-8
"""
向域名的权威域名服务器查询域名IP和CNAME
"""
import random
import dns.query
import dns.resolver
from is_legal_ip import judge_legal_ip
from resolving_ip_cname_by_dns import obtaining_domain_ip


def query_ip_cname_by_ns (domain, authoritative_ns, local_dns = '1.2.4.8', timeout=2, retry_time=2):
    """
    向域名的NS权威服务器查询域名的IP记录，若有CNAME，则获取CNAME的记录
    :parameter
    domain: 要查询的域名，注意为全域名
    authoritative_ns: 域名的权威服务器地址，可能为域名或IP
    timeout:超时时间
    retry_time：重试次数
    """

    ipv4, cnames = [], []
    ip_cname_status = 'FALSE'

    if not judge_legal_ip(authoritative_ns):  # 若为域名，则先解析出来权威服务器的IP
        authoritative_ip, _, auth_ip_cname_status = obtaining_domain_ip(authoritative_ns, local_dns)
        if auth_ip_cname_status != "TRUE":
            return ipv4, cnames, ip_cname_status
    else:
        authoritative_ip = [authoritative_ns]

    query = dns.message.make_query(domain, dns.rdatatype.A,use_edns=True)
    for _ in range(retry_time): # 重试次数
        try:
            authoritative_ns = random.choice(authoritative_ip)  # 随机选择一个IP地址
            response = dns.query.udp(query, authoritative_ns, timeout=timeout)
            for rrset in response.answer:
                r = str(rrset.to_text())
                for i in r.split('\n'):  # 注意
                    i = i.split(' ')
                    rc_type, rc_data, rc_ttl = i[3], i[4], i[1]
                    if rc_type == 'A':
                        ipv4.append(rc_data)
                    elif rc_type == 'CNAME':
                        cnames.append(rc_data[:-1].lower())
            ipv4.sort()
            ip_cname_status = 'TRUE'
            break
        except dns.resolver.NoAnswer:
            ip_cname_status = 'NO ANSWERS'
        except dns.resolver.NXDOMAIN:
            ip_cname_status = "NXDOMAIN"  # 只执行一次
            break
        except dns.resolver.NoNameservers:
            ip_cname_status = 'NO NAMESERVERS'
        except dns.resolver.Timeout:
            ip_cname_status = 'TIMEOUT'
        except:
            ip_cname_status = 'UNEXPECTED ERRORS'

    return ipv4, cnames, ip_cname_status


if __name__ == '__main__':

    # print query_ip_cname_by_ns ('www.baidu.com', authoritative_ns='202.108.22.220')
    print query_ip_cname_by_ns ('www.baidu.com', authoritative_ns='ns3.baidu.com')
    print query_ip_cname_by_ns ('www.hao123.com', authoritative_ns='dns.baidu.com')
    print query_ip_cname_by_ns ('www.hitwh.edu.cn', authoritative_ns='dns1.hitwh.edu.cn')

    # print query_ip_cname_by_ns ('www.toutiao.com', authoritative_ns='1.2.4.8')
    print query_ip_cname_by_ns('www.zhihu.com',authoritative_ns='ns3.dnsv5.com')