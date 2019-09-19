# encoding:utf-8
"""
获取根服务器和顶级域名的权威服务器信息
"""

import schedule
from obtaining_tlds_ns_from_zone import *
from obtaining_tlds_ns_from_root import *
from db_manage.data_base import MySQL
from db_manage.mysql_config import SOURCE_CONFIG_LOCAL as SOURCE_CONFIG


def insert_tld_ns_db(db, tld_result):
    """更新数据到数据库中"""

    sql = 'INSERT INTO tld_ns_zone (tld,server_name,server_ipv4,server_ipv6) VALUES (%s,%s,%s,%s) \
            ON DUPLICATE KEY UPDATE server_name=values (server_name),server_ipv4 =values (server_ipv4),server_ipv6=VALUES (server_ipv6) '
    try:
        db.update_many(sql, tld_result)
        logger.logger.info("更新数据库成功")
    except:
        logger.logger.error("更新数据库失败")


def insert_root_ns_db(db,root_ns,root_a, root_aaaa):
    """将根服务器信息存入数据库中"""
    for i,n in enumerate(root_ns):
        ns_name = str(n)
        ipv4 = str(root_a[i])
        ipv6 = str(root_aaaa[i])
        sql = 'INSERT INTO root_server (server_name,server_ipv4,server_ipv6) VALUES ("%s","%s","%s") \
                    ON DUPLICATE KEY UPDATE server_ipv4 ="%s",server_ipv6="%s" '
        try:
            db.update(sql % (ns_name, ipv4, ipv6, ipv4, ipv6))
            logger.logger.info("更新数据库成功")
        except:
            logger.logger.error("更新数据库失败")


def main():
    result = []
    tld_result1 = extract_ns_ip_by_root()  # 通过询问根域名服务器获得数据, todo 不能有这种命名
    tld_result2 = get_tld_ns_by_zone()     # 通过下载zone文件获得数据
    # 取两个结果的并集
    for i in tld_result1:
        for t in tld_result2:
            if i[0] == t[0]:
                ns_list1 = i[1].split(';')  # 将字符串变为列表然后取并集
                ns_list = list(set(ns_list1) | set(t[1]))
                ns_str = ';'.join(ns_list)  # 列表变为字符串
                ipv4_list1 = i[2].split(';')  # 将字符串变为列表然后取并集
                ipv4_list = list(set(ipv4_list1) | set(t[2]))
                ipv4_str = ';'.join(ipv4_list)  # 列表变为字符串
                ipv6_list1 = i[3].split(';')  # 将字符串变为列表然后取并集
                ipv6_list = list(set(ipv6_list1) | set(t[3]))
                ipv6_str = ';'.join(ipv6_list)  # 列表变为字符串
                result.append((i[0], ns_str, ipv4_str, ipv6_str))
    # for i in result:
    #     print i
    try:
        db = MySQL(SOURCE_CONFIG)
    except:
        logger.logger.error("数据库异常：获取域名失败")
        return
    insert_tld_ns_db(db, tld_result1)
    root_ns,root_ipv4,root_ipv6 = get_root()
    insert_root_ns_db(db, root_ns, root_ipv4, root_ipv6)
    db.close()


if __name__ == '__main__':
    # 获取顶级域名权威信息
    main()
    # schedule.every(1800).seconds.do(main)  # 下载zone文件
    # while True:
    #     schedule.run_pending()
    #     time.sleep(5)
