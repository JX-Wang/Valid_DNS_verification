# encoding:utf-8

"""
利用dns递归服务器，解析出域名的IP
"""

import dns
import dns.resolver


class DomainRecord(object):
    """获取域名的DNS记录，默认本地递归服务器为1.2.4.8，超时时间为3s，重试次数为3次"""
    def __init__(self, original_domain, local_dns='1.2.4.8', timeout=2, retry_time=2):
        self.original_domain = original_domain   # 原始域名
        self.aaaa, self.cnames = [], []
        self.status = 'FALSE'
        self.local_dns = local_dns
        self.retry_time = retry_time

        # 初始化解析器，设置本地递归服务器地址
        if local_dns:
            self.resolver = dns.resolver.Resolver(configure=False)
            self.resolver.nameservers = [self.local_dns]  # 自定义本地递归服务器
        else:
            self.resolver = dns.resolver.Resolver()  # 系统默认的递归服务器

        self.resolver.timeout, self.resolver.lifetime = timeout, timeout  # 超时时间

    def fetch_rc_ttl(self):
        """获取域名的dns记录"""
        self.obtaining_a_cname_rc()

    def return_domain_rc(self):
        """返回域名的DNS记录"""
        return self.aaaa, self.cnames, self.status

    def obtaining_a_cname_rc(self):
        """
        获取域名的A和CNAME记录
        """
        for _ in range(self.retry_time):  # 尝试3次
            try:
                resp_a = self.resolver.query(self.original_domain, 'AAAA')
                for r in resp_a.response.answer:
                    r = str(r.to_text())
                    for i in r.split('\n'):  # 注意
                        i = i.split(' ')
                        rc_type,rc_data,rc_ttl = i[3], i[4],i[1]
                        if rc_type == 'AAAA':
                            self.aaaa.append(rc_data)
                        elif rc_type == 'CNAME':
                            self.cnames.append(rc_data[:-1])
                self.aaaa.sort()
                self.status = "TRUE"
                break
            except dns.resolver.NoAnswer:
                self.status = 'NO ANSWERS'
            except dns.resolver.NXDOMAIN:
                self.status = "NXDOMAIN"  # 尝试一次
                break
            except dns.resolver.NoNameservers:
                self.status = 'NO NAMESERVERS'  # 尝试一次
                break
            except dns.resolver.Timeout:
                self.status = 'TIMEOUT'
            except:
                self.status = 'UNEXPECTED ERRORS'


def obtaining_domain_aaaa(original_domain, local_dns=None):
    """
    获取域名dns记录，local_dns：必须为列表
    """
    if local_dns is None:
        local_dns = []
    domain_obj = DomainRecord(original_domain, local_dns)
    domain_obj.fetch_rc_ttl()
    return domain_obj.return_domain_rc()


if __name__ == '__main__':
    print obtaining_domain_aaaa('www.baidu.com', local_dns='114.114.114.114')
    print obtaining_domain_aaaa('www.hitwh.edu.cn', local_dns='47.94.47.91')
    print obtaining_domain_aaaa('www.taobao.com', local_dns='2001:da8:7007:107::77')

