#encoding:utf-8
"""
通过向各个层次的权威NS地址查询，获取域名的NS记录。
可以配置为在线和离线查询
目前只支持域名是主域名
"""

import dns
import random
import dns.name
import dns.query
import dns.resolver
from collections import defaultdict

def get_authoritative_nameserver(domain, offline=False, tld_server = None, default_dns = None, retry_times=1):
    """
    通过向各个权威NS发送查询请求，获取域名的NS记录
    :param domain: 要查询的域名，目前只支持注册域名的权威查询
    :param offline: 是否离线查询，在线表示顶级域名的权威通过配置好的递归服务器获取；离线表示顶级域名的权威地址由输入确定
    :param tld_server: 若为离线查询，则tld_server为指定的顶级域名权威IP地址，务必为IP
    :param retry_times: 重试次数
    :return: rrset ，域名的NS记录
    """
    domain_dns_rc = {
        'ns_rc': '',
        'ns_rc_ip': ''
    }

    if offline and not tld_server: # 若使用离线数据，但顶级域名权威为空，则输出错误
        return '顶级域名权威地址IP不能为空', domain_dns_rc

    n = dns.name.from_text(domain)
    if len(n) == 1:
        return "域名的顶级域名不存在", domain_dns_rc
    depth = 2
    rrset = None
    if default_dns:
        nameservers = [default_dns, '114.114.114.114', '223.5.5.5','119.29.29.29','180.76.76.76']
    else:
        nameservers = ['114.114.114.114', '223.5.5.5','119.29.29.29','180.76.76.76']
    nameserver = default_dns  # 初始化dns
    default = dns.resolver.Resolver(configure=False) # 自定义本地递归服务器
    default.timeout = 2
    random.shuffle(nameservers)
    default.nameservers = nameservers

    while True:
        s = n.split(depth)
        last = s[0].to_unicode() == u'@'
        sub = s[1]
        if len(sub) == 2:  # 若为顶级域名，且为offline，则使用指定的顶级域名权威查询域名的ns
            if offline:
                nameserver = tld_server
                depth += 1
                continue
        # query = dns.message.make_query(sub, dns.rdatatype.NS, use_edns=True) # 增加使用edns
        query = dns.message.make_query(sub, dns.rdatatype.NS)
        try:
            response = dns.query.udp(query, nameserver, timeout=2)
        except:
            if retry_times:
                retry_times = retry_times - 1
                if not rrset:
                    continue
                # 重新选择一个ns地址
                rrset_cnt = len(rrset)  # rrset的大小
                random_serial = random.randint(0, rrset_cnt - 1)
                rr = rrset[random_serial]  # 随机选择一条记录
                try:
                    authority = rr.target
                except Exception,e:
                    return str(e),domain_dns_rc
                try:
                    nameserver = default.query(authority).rrset[0].to_text()
                except:
                    try:
                        nameserver = default.query(authority).rrset[0].to_text()
                    except:
                        return "resovling nameserver failed",domain_dns_rc
                continue
            else:
                return 'TIMEOUT', domain_dns_rc

        retry_times = 1  # 若成功，则重新初始化超时重试次数
        rcode = response.rcode()
        if rcode != dns.rcode.NOERROR:
            if rcode == dns.rcode.NXDOMAIN:
                # print  '%s does not exist.' % sub
                return 'NOEXSIT', domain_dns_rc
            else:
                return 'Error %s' % dns.rcode.to_text(rcode), domain_dns_rc
        try:  # 新增加异常判断
            if len(response.authority) > 0:
                rrset = response.authority[0]
            else:
                rrset = response.answer[0]
        except Exception, e:
            return str(e), domain_dns_rc
        if last:
            try:
                if len(response.additional) > 0:
                    rrset_ip = response.additional
                else:
                    rrset_ip = ''
            except:
                rrset_ip = ''

            domain_dns_rc['ns_rc'] = rrset
            domain_dns_rc['ns_rc_ip'] = rrset_ip
            return True, domain_dns_rc

        rrset_cnt = len(rrset) # rrset的大小
        random_serial = random.randint(0, rrset_cnt-1)  # 根据长度，随机选择一个序号
        rr = rrset[random_serial]  # 随机选择一条记录
        if rr.rdtype == dns.rdatatype.SOA:
            # print 'Same server is authoritative for %s' % sub
            pass
        else:
            try:
                authority = rr.target
            except:
                return 'authority soa target error',domain_dns_rc
            # print '%s is authoritative for %s' % (authority, sub)
            try:
                nameserver = default.query(authority).rrset[0].to_text()
            except:
                try:
                    nameserver = default.query(authority).rrset[0].to_text()
                except:
                    return "resovling nameserver failed",domain_dns_rc
        depth += 1


def parse_rc_ns(domain_dns_rc):
    """解析出域名的NS集合"""

    # 解析出ns的IP信息
    ns_rc_ip = domain_dns_rc['ns_rc_ip']
    ns_ip = defaultdict(list)
    if ns_rc_ip: # 不为空
        try:
            for i in ns_rc_ip:
                r = str(i.to_text())
                for i in r.split('\n'):  # 注意
                    i = i.split(' ')
                    rc_name, rc_type, rc_data = i[0].lower()[:-1], i[3], i[4]
                    if rc_type == 'A':
                        ns_ip[rc_name].append(rc_data)
        except Exception,e:
            print str(e)

    # 解析出ns信息
    rrset = domain_dns_rc['ns_rc']
    ns = []
    respond_main_domain = ""
    if rrset:
        r = str(rrset.to_text())
        for i in r.split('\n'):
            i = i.split(' ')
            rc_type, rc_ttl = i[3], i[1]
            if rc_type == 'NS':
                ns.append((i[4][:-1]).lower())
                respond_main_domain = i[0][:-1]
        ns.sort()
    return respond_main_domain, ns, ns_ip


def get_domain_ns_hierarchical_dns(main_domain, offline = False, tld_server=None, default_dns=None):
    """按照DNS的分布层级，获取域名NS记录"""
    flag, domain_dns_rc = get_authoritative_nameserver(main_domain,offline,tld_server,default_dns)
    if flag == True:
        respond_main_domain, ns, ns_ip = parse_rc_ns(domain_dns_rc)
        if main_domain == respond_main_domain:
            return [ns, ns_ip], 'TRUE'
        else:
            return [[], {}], 'FALSE'
    else:
        # print '域名: %s, 异常原因：%s' % (domain, rrset)
        return [[], {}], flag


if __name__ == '__main__':
    domain = 'baidu.com'
    print get_domain_ns_hierarchical_dns(domain, offline=True, tld_server='192.26.92.30')  #offline模式