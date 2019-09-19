#encoding:utf-8
"""
向域名的权威域名服务器查询域名IP和CNAME
"""
import dns
import random
import dns.query
import dns.resolver
from is_legal_ip import judge_legal_ip
from resolving_ip_cname_by_dns import obtaining_domain_ip


def query_domain_ns_by_ns (domain, original_ns, local_dns=None, timeout=2):
    """
    向域名的NS权威服务器查询域名的IP记录，若有CNAME，则获取CNAME的记录
    :parameter
    domain: 要查询的域名，注意为主域名
    authoritative_ns: 域名的权威服务器地址，可能为域名或IP
    timeout:超时时间
    retry_time：重试次数
    """

    domain_ns = []
    ns_status = 'FALSE'
    authoritative_ns = original_ns
    if not judge_legal_ip(authoritative_ns):  # 若为域名，则先解析出来权威服务器的IP
        authoritative_ip, _, auth_ip_cname_status = obtaining_domain_ip(authoritative_ns,local_dns)
        if auth_ip_cname_status != "TRUE":
            return domain_ns, ns_status,original_ns
    else:
        authoritative_ip = [authoritative_ns]

    # query = dns.message.make_query(domain, dns.rdatatype.NS, use_edns=True)
    query = dns.message.make_query(domain, dns.rdatatype.NS)
    try:
        authoritative_ns = random.choice(authoritative_ip)  # 随机选择一个IP地址
        response = dns.query.udp(query, authoritative_ns, timeout=timeout)
        # print response.flags & dns.flags.AA
        for rrset in response.answer:
            r = str(rrset.to_text())
            for i in r.split('\n'):  # 注意
                i = i.split(' ')
                rc_type, rc_data = i[3], i[4]
                if rc_type == 'NS':
                    domain_ns.append(rc_data[:-1])
        ns_status = 'TRUE'
    except dns.resolver.NoAnswer:
        ns_status = 'NO ANSWERS'
    except dns.resolver.NXDOMAIN:
        ns_status = "NXDOMAIN"  # 只执行一次
    except dns.resolver.NoNameservers:
        ns_status = 'NO NAMESERVERS'
    except dns.resolver.Timeout:
        ns_status = 'TIMEOUT'
    except:
        ns_status = 'UNEXPECTED ERRORS'

    return domain_ns, ns_status, original_ns


if __name__ == '__main__':

    print query_domain_ns_by_ns ('baidu.com', '222.194.15.9')
    print query_domain_ns_by_ns ('hitwh.edu.cn','dns2.hitwh.edu.cn')
    print query_domain_ns_by_ns ('baidu.com', 'dns.baidu.com')
