# encoding:utf-8

"""
分别向顶级域名的权威和DNS递归服务器查询域名的NS记录，并且批量更新
注意：使用两种方法获取域名的NS记录，因为不同方法都无法获取完整的NS记录

"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../')
import threading
import time
import datetime
from Queue import Queue
from threading import Thread
from collections import defaultdict
from db_manage.data_base import MySQL
from db_manage.mysql_config import SOURCE_CONFIG_LOCAL as SOURCE_CONFIG
import tldextract
from Logger import Logger
from task_confirm import TaskConfirm
from resolving_domain_ns_combined import resolving_domain_ns
from resolving_ip_cname_combined import resolving_domain_ip_cname
from resolving_aaaa_cname_combined import resolving_domain_aaaa_cname
from resolving_domain_soa_by_ns import resolving_domain_soa
from resolving_domain_mx_by_ns import resolving_domain_mx

lock = threading.Lock()

domain_dns_rc_set = []
thread_num = 50   # 主线程数量
queue = Queue()  # 任务队列
logger = Logger(file_path='./query_log/',show_terminal=True)  # 日志配置


class ResultThread(threading.Thread):
    """自定义线程类，用于返回结果"""
    def __init__(self,func,args=()):
        super(ResultThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception,e:
            logger.logger.error('获取线程的结果失败:',str(e))
            return [], [], [], []



class SOAThread(threading.Thread):
    """自定义线程类，用于返回结果"""
    def __init__(self,func,args=()):
        super(SOAThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception,e:
            logger.logger.error('获取线程的结果失败:',str(e))
            return ''



class MXThread(threading.Thread):
    """自定义线程类，用于返回结果"""
    def __init__(self,func,args=()):
        super(MXThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception,e:
            logger.logger.error('获取线程的结果失败:',str(e))
            return []


def read_domains(file_name):
    """
    读取域名存储文件，获取要探测的域名，以及提取出主域名
    注意：若是不符合规范的域名，则丢弃
    """
    domains = []
    main_domains = []
    tlds = []
    file_path = './unverified_domain_data/'+ file_name
    no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=None)
    try:
        with open(file_path,'r') as fp:
            for d in fp.readlines():
                try:
                    domain_tld = no_fetch_extract(d.strip())
                except:
                    continue
                tld, reg_domain = domain_tld.suffix, domain_tld.domain  # 提取出顶级域名和注册域名部分
                if tld and reg_domain:
                    main_domains.append(reg_domain+'.'+tld)
                    domains.append(d.strip())
                    if '.' in tld:
                        first_tld = tld.split('.')[-1]
                        tlds.append(first_tld)
                    else:
                        tlds.append(tld)
                else:
                    logger.logger.warning('域名%s不符合规范，不进行探测' % d.strip())
    except IOError, e:
        logger.logger.error('文件不存在：'+str(e))

    return domains, main_domains, tlds


def fetch_tld_ns():
    """
    获取顶级域名的权威服务器（ns）IP地址
    """

    tld_ns = defaultdict(set)
    try:
        db = MySQL(SOURCE_CONFIG)
        sql = 'SELECT tld,server_ipv4 from tld_ns_zone'
        db.query(sql)
        tld_ns_query = db.fetch_all_rows()  # 获取已存储的顶级域名的权威服务器信息
    except Exception, e:
        logger.logger.error("获取顶级域名异常：",e)
        return tld_ns
    db.close()
    for i in tld_ns_query:
        tld = str(i['tld'])
        if i['server_ipv4']:
            ipv4 = str(i['server_ipv4']).split(';')
            for ip in ipv4:
                for p in ip.split(','):
                    if p:
                     tld_ns[tld].add(p)
    return tld_ns


def create_queue(domains, main_domains, tlds):
    """
    创建批量探测的任务队列
    """

    for i, d in enumerate(domains):
        queue.put((d, main_domains[i], tlds[i]))


def master_control(tld_ns_set, open_dns):
    """主线程控制"""
    global domain_dns_rc_set
    while queue.qsize():
        logger.logger.info('存活线程: %s, 剩余任务: %s' % (threading.activeCount(),queue.qsize()))
        domain, main_domain, tld = queue.get()
        tld_ns = tld_ns_set.get(tld)  # 得到顶级域名的权威服务器域名地址集合
        if tld_ns:
            # 获取域名的NS记录
            domain_ns_result = resolving_domain_ns(domain, main_domain, tld_ns)
            domain_ns = domain_ns_result['domain_ns']  # 提取域名有效ns记录
            if domain_ns:
                # 获取域名的A和CNAME记录，特别注意子线程共享变量的问题
                a_cname_worker = ResultThread(resolving_domain_ip_cname, args=(domain, domain_ns, open_dns))
                a_cname_worker.setDaemon(True)
                a_cname_worker.start()


                # 获取域名的AAAA和CNANE记录
                aaaa_cname_worker = ResultThread(resolving_domain_aaaa_cname, args=(domain, domain_ns, open_dns))
                aaaa_cname_worker.setDaemon(True)
                aaaa_cname_worker.start()

                # 获取域名的SOA记录
                soa_worker = SOAThread(resolving_domain_soa, args=(main_domain, domain_ns))
                soa_worker.setDaemon(True)
                soa_worker.start()

                # 获取域名的mx记录
                mx_worker = MXThread(resolving_domain_mx, args=(main_domain, domain_ns))
                mx_worker.setDaemon(True)
                mx_worker.start()
                # 在这里增加新的域名记录

                # 获取域名的记录结果
                a_cname_worker.join()
                domain_ips, domain_a_cnames, unknown_ips, unknown_cnames = a_cname_worker.get_result()
                aaaa_cname_worker.join()
                domain_aaaa, domain_aaaa_cnames, unknown_ips, unknown_cnames = aaaa_cname_worker.get_result()
                soa_worker.join()
                domain_soa = soa_worker.get_result()
                mx_worker.join()
                domain_mx = mx_worker.get_result()
                # 在这里添加新的域名记录结果

                # 组合
                domain_dns_rc = {'domain': domain}
                if domain_ns:
                    domain_dns_rc['NS'] = ','.join(domain_ns)
                if domain_ips:
                    domain_dns_rc['A'] = ','.join(domain_ips)
                if domain_a_cnames or domain_aaaa_cnames:
                    domain_dns_rc['CNAME'] = ','.join(list(set(domain_aaaa_cnames+domain_a_cnames)))
                if domain_aaaa:
                    domain_dns_rc['AAAA'] = ','.join(domain_aaaa)
                if domain_soa:
                    domain_dns_rc['SOA'] = domain_soa
                if domain_mx:
                    domain_dns_rc['MX'] = ','.join(domain_mx)

                domain_dns_rc_set.append(domain_dns_rc)
            else:
                logger.logger.info('无有效NS服务器，域名：'+ domain)
        else:
            logger.logger.info('无此域名：%s的顶级域名权威服务器地址'% domain)

        queue.task_done()  # 此次任务完成


def save_to_file(id):
    """
    将探测得到的域名的DNS记录存入到本地文件中
    :param id: string, 任务ID号
    """
    insert_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    path = './verified_domain_data/'
    file_name = id+'_'+ insert_time
    try:
        fp = open(path+file_name, 'w')
        for rc in domain_dns_rc_set:
            domain = rc.pop('domain')  # 得到域名，并从字典中删除
            for k in rc:
                fp.write(domain+'\t'+ k +'\t'+rc[k]+'\n')
        fp.close()
        return file_name
    except Exception, e:
        logger.logger.error(str(e))
        return False


def read_domain_dns_rc(file_name):
    """
    读取域名的DNS记录
    :param: file_name, string, 保存的文件名称
    """
    path = './verified_domain_data/'
    try:
        with open(path+file_name,'r') as fp:
            domain_dns_rc = fp.read()
            return domain_dns_rc
    except Exception, e:
        logger.logger.error('读取失败：'+str(e))
        return []


def obtaining_domain_dns_rc(domains, main_domains,tlds, tld_ns, open_dns):
    """
    获取域名的dns记录，采用多线程（全局变量）
    :param domains: list， 域名集合
    :param main_domains: list, 域名对应的主域名
    :param tlds: list, 域名对应的顶级域名
    :param tld_ns: dict, 顶级域名对应的权威服务器IP地址
    :param open_dns: list, 开放DNS递归服务器集合
    """
    create_queue(domains, main_domains, tlds)  # 创建任务队列
    # worker_list = []
    for q in range(thread_num):  # 开始任务
        worker = Thread(target=master_control,args=(tld_ns, open_dns))
        worker.setDaemon(True)
        worker.start()
        # worker_list.append(worker)

    queue.join()


def read_dns():
    """
    读取开放DNS递归服务器IP地址集合
    """
    dns = []
    try:
        with open('../domain_dns_http/ODNS.txt','r') as f:
            for i in f.readlines():
                dns.append(i.strip())
    except Exception, e:
        logger.logger.error(str(e))

    if not dns:  # 若文件无dns，则默认开放的dns服务器
        dns.extend(['1.2.4.8','114.114.114.114','223.5.5.5'])
    return dns


def get_domain_dns_rc(file_name, id):
    """
    获取域名的dns记录，并存储到本地或者数据库
    :param file_name: sting，要探测的域名存储文件地址
    :param id: string，本次任务id号
    """

    logger.logger.info('开始解析任务：%s的域名的DNS记录' % id)

    tld_ns_set = fetch_tld_ns()
    open_dns = read_dns()
    domains, main_domains,tlds = read_domains(file_name)  # 获取要探测域名与其主域名
    obtaining_domain_dns_rc(domains, main_domains, tlds, tld_ns_set, open_dns)

    logger.logger.info('保存结果到文件中...')
    save_file_name = save_to_file(id)
    if save_file_name:
        logger.logger.info('保存成功')
        for _ in range(3):  # 重试三次
            domain_ns = read_domain_dns_rc(save_file_name)
            flag = TaskConfirm(save_file_name, domain_ns, 'query', id).task_confirm()  # 确认探测完成消息
            if isinstance(flag, bool):  # 成功则停止发送
                logger.logger.info('任务：%s,确认成功' % str(id))
                break
            else:
                logger.logger.error('任务：%s,确认探测失败,原因：%s' % (str(id), flag))
    else:
        logger.logger.error('保存失败,任务ID为:'+str(id))

    logger.logger.info('结束解析任务：%s的域名的DNS记录' % id)


if __name__ == '__main__':
    file_name = sys.argv[1]
    id = sys.argv[2]
    get_domain_dns_rc(file_name, id)
