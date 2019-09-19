# encoding:utf-8

"""
将域名数据导入到数据库中
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../')

from db_manage.data_base import MySQL
from db_manage.mysql_config import SOURCE_CONFIG_LOCAL as SOURCE_CONFIG
import tldextract
from Logger import Logger

logger = Logger(file_path='./query_log/', show_terminal=True)  # 日志配置


def read_domains(file_name):
    """
    读取域名存储文件，获取要探测的域名，以及提取出主域名
    注意：若是不符合规范的域名，则丢弃
    """
    domains = []
    main_domains = []
    no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=None)
    file_path = './unverified_domain_data/'
    with open(file_path+file_name,'r') as fp:
        for d in fp.readlines():
            domain_tld = no_fetch_extract(d.strip())
            tld, reg_domain = domain_tld.suffix, domain_tld.domain  # 提取出顶级域名和主域名部分
            if tld and reg_domain:
                main_domains.append(reg_domain+'.'+tld)
                domains.append(d.strip())
            else:
                logger.logger.warning('域名%s不符合规范，不进行探测' % d.strip())

    return domains, main_domains


def insert_domains_db(domains):
    """将域名插入到数据库中"""
    try:
        db = MySQL(SOURCE_CONFIG)
    except Exception,e:
        logger.logger.error(e)
        return False
    for domain in domains:
        sql = 'insert ignore into focused_domain (domain) values ("%s")' % (domain)
        db.insert_no_commit(sql)
    db.commit()
    db.close()
    return True


def manage_domains(file_name):
    """主函数"""
    logger.logger.info('开始导入域名数据，文件名称:%s' % file_name)

    domains, main_domains = read_domains(file_name)
    if insert_domains_db(domains):
        logger.logger.info("成功将域名更新到数据库")
    else:
        logger.logger.info('将域名更新到数据库失败')

    logger.logger.info('结束导入域名数据，文件名称:%s' % file_name)


def main():
    # file_name = '../domain_data/domains_201907011111'
    file_name = '../domain_data/top500.txt'
    # file_name = '../domain_data/test2.txt'
    manage_domains(file_name)


if __name__ == '__main__':
    # main()
    file_name = sys.argv[1]
    manage_domains(file_name)