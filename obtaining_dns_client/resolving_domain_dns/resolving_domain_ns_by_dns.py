# encoding:utf-8
"""
利用DNS递归服务器，获取域名的NS服务器
"""
import dns.resolver
import tldextract
import random
from collections import defaultdict
def extract_main_domain(domain):
    """提取主域名"""
    no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=None)
    domain_tld = no_fetch_extract(domain)
    main_domain = ""
    if domain_tld.suffix:
        if domain_tld.domain:
            main_domain = domain_tld.domain+'.'+domain_tld.suffix

    return main_domain


def obtaining_domain_ns_name(main_domain, retry_times=1, timeout=2):
    """
    根据域名，获取其顶级域名的权威服务器地址
    root_ip 数据类型为list
    """

#    main_domain = extract_main_domain(domain)
    ns = []
    ns_ip = defaultdict(list)
    ns_status = 'FALSE'
    if not main_domain:  # 主域名不存在
        return ns, ns_status

    resolver = dns.resolver.Resolver(configure=False)
    resolver.timeout = timeout
    resolver.lifetime=timeout*3
    nameservers = ['114.114.114.114','1.2.4.8','119.29.29.29','180.76.76.76']
    #resolver.nameservers = recursion_server

    for _ in range(retry_times):  # 尝试3次
        try:
            random.shuffle(nameservers)
            resolver.nameservers = nameservers
            dns_resp = dns.resolver.query(main_domain, 'NS')
            try:
                for i in dns_resp.response.additional:
                    r = str(i.to_text())
                    for i in r.split('\n'):  # 注意
                        i = i.split(' ')
                        rc_name, rc_type, rc_data = i[0].lower()[:-1], i[3], i[4]
                        if rc_type == 'A':
                            ns_ip[rc_name].append(rc_data)
            except Exception, e:
                print str(e)
            for r in dns_resp.response.answer:
                r = str(r.to_text())
                for i in r.split('\n'):
                    i = i.split(' ')
                    ns_domain, rc_type = i[0], i[3]
                    if ns_domain[:-1] != main_domain:
                        continue
                    if rc_type == 'NS':
                        ns.append(str(i[4][:-1]).lower())
            ns_status = 'TRUE'
            ns.sort()
            break
        except dns.resolver.NoAnswer:
            ns_status = 'NO ANSWERS'
        except dns.resolver.NXDOMAIN:
            ns_status = "NXDOMAIN"  # 尝试一次
            break
        except dns.resolver.NoNameservers:
            ns_status = 'NO NAMESERVERS'  # 尝试一次
            break
        except dns.resolver.Timeout:
            ns_status = 'TIMEOUT'
        except Exception, e:
            ns_status = 'UNEXPECTED ERRORS:'+str(e)

    return ns, ns_ip, ns_status


if __name__ == '__main__':
    print obtaining_domain_ns_name('baidu.com')
