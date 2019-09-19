# encoding:utf-8
import dns
import dns.name
import dns.query
import dns.resolver


def get_authoritative_nameserver(domain,tld_ns_ip):
    n = dns.name.from_text(domain)
    depth = 3  # 从域名的第三级开始，包括根，例如www.baidu.com，则是从baidu.com.进行探测
    default = dns.resolver.get_default_resolver()
    nameserver = tld_ns_ip
    is_last = False
    while not is_last:
        s = n.split(depth)
        is_last = s[0].to_unicode() == u'@'  # 是否到最后一级
        sub_domain = s[1]

        print 'Looking up %s on %s' % (sub_domain, nameserver)
        query = dns.message.make_query(sub_domain, dns.rdatatype.NS)
        try:
            response = dns.query.udp(query, nameserver, timeout=2)
        except dns.resolver.Timeout:
            return "TIMEOUT"
        except Exception, e:
            return 'ERROR:%s' % str(e)

        rcode = response.rcode()
        if rcode != dns.rcode.NOERROR:
            if rcode == dns.rcode.NXDOMAIN:
                return 'NXDOMAIN'
            else:
                return 'ERROR:%s' % dns.rcode.to_text(rcode)

        for i in response.authority:
            print i
        print '99999'
        print response.answer
        if len(response.authority) > 0:
            rrset = response.authority[0]
        else:
            rrset = response.answer[0]

        rr = rrset[0]
        if rr.rdtype == dns.rdatatype.SOA:
            print 'Same server is authoritative for %s' % sub_domain
        else:
            authority = rr.target
            print '%s is authoritative for %s' % (authority, sub_domain)
            nameserver = default.query(authority).rrset[0].to_text()

        depth += 1

    return nameserver


domain = 'baidu.com'
tld_ns_ip = '192.26.92.30'
print get_authoritative_nameserver(domain, tld_ns_ip)