# encoding : utf-8
"""
Integration result files
========================
Author @ Wangjunxiong
TBegin @ 2019.8.13
TheEnd @ 2019.8.22 1.0
TheEnd @ 2019.8.27 2.0
"""

import os
import schedule
import time
import hashlib
from multiprocessing import Process

# Third party python lib
from confluent_kakfa_tools import confluent_kafka_producer
from read_config import *
from saving_domain_dns import monitor_kafka_data
from compare_data import compare_data
from Logger import Logger
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

TIMEOUT = 1800  # global time out
FREQUENT = 10  # seconds
PRODUCER_RETRY_TIMES = 3  # Max retry time 3


class IntergrationResultFiles:
    """
    IntergrationResultFiles
    This class is for gathering all the data files in a single file which named by it's task id
    :param str ORIGINDICT: original dict
    :param str RSTDICT: Final Task dict, every file contains total data
    :rtype None
    :return None
    """
    def __init__(self, ORIGIN_DICT=ORIGIN_DICT, RSTDICT=None):
        """
        IntergrationResultFiles
        .. py: __init__ function: checking the dict has been created or not, create those folder if not exists
        """
        query_folder = os.path.exists(ORIGIN_DICT+QUERY_TASK)
        if not query_folder:
            os.mkdir(ORIGIN_DICT+QUERY_TASK)

        sec_folder = os.path.exists(ORIGIN_DICT+SEC_TASK)
        if not sec_folder:
            os.mkdir(ORIGIN_DICT+SEC_TASK)

        sec_merged_folder = os.path.exists(ORIGIN_DICT + SEC_TASK_MERGED)
        if not sec_merged_folder:
            os.mkdir(ORIGIN_DICT + SEC_TASK_MERGED)

        query_merged_folder = os.path.exists(ORIGIN_DICT + QUERY_TASK_MERGED)
        if not query_merged_folder:
            os.mkdir(ORIGIN_DICT + QUERY_TASK_MERGED)

        sec_compared_folder = os.path.exists(ORIGIN_DICT + SEC_TASK_COMPARED)
        if not sec_compared_folder:
            os.mkdir(ORIGIN_DICT + SEC_TASK_COMPARED)

        else:
            pass

    def resolve_dict_task_id(self, dir_name):
        merge_file_dict, task_id = '', ''
        if QUERY_TASK in dir_name:
            merge_file_dict = QUERY_TASK_MERGED
            task_id = dir_name.replace(QUERY_TASK, '')
        elif SEC_TASK in dir_name:
            merge_file_dict = SEC_TASK_MERGED
            task_id = dir_name.replace(SEC_TASK, '')
        else:
            logger.logger.error("Merge file Error")
        return merge_file_dict, task_id

    def produce(self, dir_name):
        """
        :param filename:
        :return: bool:
        """
        merge_file_dict, task_id = self.resolve_dict_task_id(dir_name)

        file_url = "http://{ip}:{port}/file_/{file_name}".format(ip=IP, port=str(PORT),
                                                                file_name=merge_file_dict+task_id)  # file url

        with open(ORIGIN_DICT+merge_file_dict+task_id) as f:
            domain_data = f.read()
            file_md5 = hashlib.md5(domain_data.encode("utf-8")).hexdigest()

        task_type = dir_name.replace('/'+task_id, '')
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

    def monitor(self):
        while True:
            self.do()
            time.sleep(FREQUENT)

    def get_total_num(self, filename):
        """
        :param filename -> str
        :return: total num -> int
        """
        filename = str(filename)
        if not filename:
            logger.logger.error("Error Empty File Name")
        else:
            pass
        try:
            tmp = filename.split("_")[-1]
            return int(tmp)
        except Exception as e:
            logger.logger.error("Resolve File Name Error" + str(e))
            return

    def merge_files(self, dir_name):
        """
        :return: bool:
        """
        print "dir_name is ", dir_name
        merge_file_dict, task_id = self.resolve_dict_task_id(dir_name)

        merge_file_name = ORIGIN_DICT + merge_file_dict + task_id  # merge dict
        data_files_list = os.listdir(ORIGIN_DICT + dir_name)  # source dict

        try:
            for datafile in data_files_list:
                try:
                    f_tmp = open(ORIGIN_DICT+dir_name+"/"+datafile, 'r')
                    data_rst = f_tmp.read()
                    f = open(merge_file_name, "a+")
                    f.write(data_rst)
                    f_tmp.close()
                    f.close()
                except Exception as e:
                    logger.logger.error("Merge data error"+str(e))
                # f.writelines("\n")
                    return
        except Exception as e:
            logger.logger.error("AddFile Error"+str(e))
            return

    def do(self):
        msg = [QUERY_TASK, SEC_TASK]
        for dir_name in msg:
            if dir_name == QUERY_TASK:  # dealing with query task
                id_dict = os.listdir(ORIGIN_DICT + dir_name[:-1])
                for task_id in id_dict:
                    task_files = os.listdir(ORIGIN_DICT+dir_name+task_id)
                    if "Done" in task_files:  # means this SOURCE has been finished
                        continue
                    total_num = self.get_total_num(task_files[0])  # get the total files num

                    if total_num >= len(task_files):  # if this task done
                        self.merge_files(dir_name=dir_name+task_id)  #
                        for i in range(PRODUCER_RETRY_TIMES):  # Max retry time 3
                            if self.produce(dir_name=dir_name+task_id):  # kafka producer publish rst json data
                                break
                            else:
                                pass
                            # mark this file, mean this dict has been done
                        os.system(
                            ":> " + ORIGIN_DICT + "%s/Done" % dir_name)

                    else:
                        # open the SOURCE file and check time !
                        task_files.sort(key=lambda x: int(x[:14]))
                        final_filename = task_files[0]
                        # get file create time / not fit for windows_sys
                        time_start = os.path.getctime(ORIGIN_DICT+dir_name+task_id+"/"+final_filename)
                        time_now = time.time()
                        if time_now - time_start >= TIMEOUT:
                            self.merge_files(dir_name=dir_name+task_id)
                            for i in range(PRODUCER_RETRY_TIMES):  # Max retry time 3
                                if self.produce(dir_name + task_id):  # kafka producer publish rst json data
                                    break
                                else:
                                    pass
                                # mark this file, mean this dict has been done
                            # os.system(
                            #     ":> " + ORIGIN_DICT + "%s/Done" % dir_name)
                        else:
                            pass
            # dealing with sec task
            else:
                id_dict = os.listdir(ORIGIN_DICT + dir_name[:-1])
                for task_id in id_dict:
                    task_files = os.listdir(ORIGIN_DICT + dir_name + task_id)
                    if "Done" in task_files:  # means this SOURCE has been finished
                        print "Not fodung Done"
                        continue
                    total_num = self.get_total_num(task_files[0])  # get the total files num
                    print total_num, len(task_files)
                    if total_num <= len(task_files):  # if this task done
                        print "total_num >= task_files"
                        self.merge_files(dir_name=dir_name + task_id)  #
                        # for i in range(PRODUCER_RETRY_TIMES):  # Max retry time 3
                        #     if self.produce(dir_name=dir_name+task_id):  # kafka producer publish rst json data
                        #         break
                        #     else:
                        #         pass
                        # delete this file, mean this dict has been done
                        os.system(
                                "rm -rf " + ORIGIN_DICT+dir_name+task_id)
                        # os.system(
                        # "rm -rf " + ORIGIN_DICT+'sec_merged/'+task_id)
                    else:
                        print "checking time!"
                        # open this SOURCE and check time !
                        task_files.sort(key=lambda x: int(x[:14]))
                        final_filename = task_files[0]
                        time_start = os.path.getctime(
                            ORIGIN_DICT + dir_name + task_id + "/" + final_filename)  # get file create time / not fit for windows_sys
                        time_now = time.time()
                        if time_now - time_start >= TIMEOUT:
                            self.merge_files(dir_name=dir_name + task_id)
                            # for i in range(PRODUCER_RETRY_TIMES):  # Max retry time 3
                            #     if self.produce(dir_name=dir_name+task_id):  # kafka producer publish rst json data
                            #         break
                            #     else:
                            #         pass
                            # delete this file, mean this dict has been done
                            os.system(
                                     "rm -rf " + ORIGIN_DICT+dir_name+task_id)
                            # os.system(
                            # "rm -rf " + ORIGIN_DICT+'sec_merged/'+task_id)
                        else:
                            print time_now - time_start, '<', TIMEOUT
                            pass


if __name__ == '__main__':
    task1 = Process(target=IntergrationResultFiles().monitor)
    task1.start()
    logger.logger.info("IntergrationResultFiles threading start")
    task2 = Process(target=monitor_kafka_data)
    task2.start()
    logger.logger.info("compare_data threading start")
    task3 = Process(target=compare_data().monitor)
    task3.start()
    logger.logger.info("IntergrationResultFiles threading start")
    logger.logger.info("Respond Server Monitor System Beginning 0_-")




