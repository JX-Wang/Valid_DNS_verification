# encoding : utf-8
"""
Integration result files
========================
Author @ Wangjunxiong
TBegin @ 2019.8.13
TheEnd @ 2019.8.22 1.0
TheEnd @ 2019.8.27 2.0
"""

from db_manage.mysql_config import SOURCE_CONFIG_LOCAL as SOURCE_CONFIG
from db_manage.data_base import MySQL
from confluent_kakfa_tools import confluent_kafka_producer
from read_config import *
from saving_domain_dns import monitor_kafka_data
from compare_data import compare_data
from Logger import Logger
import time
import MySQLdb
import random
import hashlib
import schedule
show_terminal = read_log_show()
logger = Logger(file_path='./query_log/', show_terminal=show_terminal)
SERVERS = read_confluent_kafka()  # kafka cluster broker config
IP, PORT = read_http_server()  # local ip & port
ORIGIN_DICT = './domain_dns_data/'
QUERY_TASK = "query/"
QUERY_TASK_MERGED = "query_merged/"
SEC_TASK = "sec/"
SEC_TASK_MERGED = "sec_merged/"
SEC_TASK_COMPARED = "sec_compared/"

TIMEOUT = 1200  # global time out
FREQUENT = 10  # seconds
PRODUCER_RETRY_TIMES = 3  # Max retry time 3


class DeliverFullNSRecoed:
    def __init__(self):
        pass

    def start(self):
        # schedule.every(10).minutes.do(self.get_ns_history_record)
        while True:
            self.get_ns_history_record()
            # schedule.run_pending()
            time.sleep(3600)
            # self.produce()
   
    def read_tld(self, db):
        data_list = []
        sql = 'SELECT tld,server_name,server_ipv4 FROM tld_ns_zone'
        try:
            db.query(sql)
            data = db.fetch_all_rows()
        except Exception as e:
            return "read tld Error" + str(e)
        for i in data:
            tld = str(i['tld'])
            ns = str(i['server_name'])
            ns_list = ns.split(';')
            ns = ','.join(ns_list)
            ns_ip = str(i['server_ipv4'])
            flag = '0'
            data_list.append((tld,ns,ns_ip,flag))
        return data_list
   
    def write_tld(self, task_id):
        try:
            db = MySQL(SOURCE_CONFIG)
        except:
            pass
        tld_list = self.read_tld(db)
        with open('./domain_dns_data/sec_compared/tld_'+task_id, 'w') as fw:
            for t in tld_list:
                fw.write(t[0]+'\t'+'NS'+'\t'+t[1]+'\t'+t[3]+'\n')
		ns_list = t[1].split(',')
		ip_list = t[2].split(';')
		for i in range(0,len(ns_list)):
		    fw.write(ns_list[i]+'\t'+'A'+'\t'+ip_list[i]+'\t'+'0'+'\n')
    def produce(self, dir_name):
        """
        :param filename:
        :return: bool:
        """
        task_id = dir_name[dir_name.index('_')+1:]

        file_url = "http://{ip}:{port}/file/{file_name}".format(ip=IP, port=str(PORT),
                                                                file_name=dir_name)  # file url

        print file_url

        with open("domain_dns_data/sec_compared/" + dir_name) as f:
            domain_data = f.read()
            file_md5 = hashlib.md5(domain_data.encode("utf-8")).hexdigest()

        task_type = 'sec'
        post_body = {
            "id": task_id,
            "time": time.time(),
            "file_url": file_url,
            "file_md5": file_md5,
            "task_type": task_type
        }

        try:
            p = confluent_kafka_producer(topic="post-pkg", servers=SERVERS, timeout=1)
            p.push(value=post_body)
        except Exception as e:
            logger.logger.error("Producer Error"+str(e))
            return False
        return True

    def get_ns_history_record(self):
        try:
            db = MySQL(SOURCE_CONFIG)
        except:
            pass
	full_list = []
        sql = 'SELECT domain,ns,ns_ip FROM domain_ns WHERE ns!=""'
	try:
            db.query(sql)
            data = db.fetch_all_rows()
        except Exception as e:
            return "read tld Error" + str(e)
	for i in data:
            tld = str(i['domain'])
            ns = str(i['ns'])
            ns_list = ns.split(';')
            ns = ','.join(ns_list)
            ns_ip = str(i['ns_ip'])
            flag = '0'
            full_list.append((tld,ns,ns_ip,flag))

        taskid = str(random.randint(10000000, 99999999))
        self.write_tld(taskid)
        new_file_name = 'full_' + taskid
        with open("domain_dns_data/sec_compared/"+new_file_name, "w") as f:
            for t in full_list:
                f.write(t[0]+'\t'+'NS'+'\t'+t[1]+'\t'+t[3]+'\n')
                ns_list = t[1].split(',')
                ip_list = t[2].split(';')
                for i in range(0,len(ns_list)):
                    f.write(ns_list[i]+'\t'+'A'+'\t'+ip_list[i]+'\t'+'0'+'\n')	
        self.produce(new_file_name)
        self.produce('tld_'+taskid)


if __name__ == '__main__':
    DeliverFullNSRecoed().start()
