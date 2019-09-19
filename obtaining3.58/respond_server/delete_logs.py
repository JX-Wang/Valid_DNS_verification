# encoding:utf-8
"""
功能：清除程序运行生成日志(满足文件大小时，默认为50M，单位为M),支持系统为Ubuntu
author: mrcheng
适用场景：
长期在后台运行的探测程序，需要进行循环探测，期间会产生程序执行日志。
使用方法：
只要放在主函数里就行，每次遍历时执行。
"""

import os
import commands
import time
import schedule
import datetime


def get_file_size(file_path):
    """获取文件的大小（M）"""
    file_path = unicode(file_path, 'utf8')
    file_size = os.path.getsize(file_path)
    file_size = file_size/float(1024*1024)
    return int(file_size)


def delete_logs(file_path, file_size_threshold=20):
    """清除超过阈值的日志文件，阈值大小默认为50M"""
    exist = os.path.exists(file_path)
    if not exist:
        print "日志文件不存在，日志自动清理功能不执行，但探测程序正常运行"
        return
    file_name = file_path.split('/')[-1]
    file_size = get_file_size(file_path)
    if file_size >= file_size_threshold:    # 超过50M 后清除
        null_command = 'cat /dev/null > ' + file_name  # 清空命令
        commands.getstatusoutput(null_command)  # 清理


def show_dir_file(dir_path,file_formate = '.out'):
    """获取目录下所有文件的名称"""
    file_sets = []
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for name in files:
            if os.path.splitext(name)[1] == file_formate:
                file_sets.append(os.path.join(root, name))
        for name in dirs:
            # print(os.path.join(root, name))
            show_dir_file(name)
    return file_sets


def get_file_path(dir_path, ignore_file=[], file_formate = '.out'):
    """
    获得后缀名为.out的文件路径
    """
    file_sets = show_dir_file(dir_path, file_formate)
    file_path = []
    for i in file_sets:
        if i.split('/')[-1] in ignore_file:
            continue
        file_path.append(i)

    return file_path


def delete_file_log(dir_path="./"):
    file_path = get_file_path(dir_path)
    for p in file_path:
        print p
        delete_logs(p)


def data_clean(folder_address="./domain_dns_data"):
    """
    删除当前目录下的domain_dns_date文件夹里的数据文件
    """
    dbtype_list = os.listdir(folder_address) # 获得当前目录下的文件与文件夹列表
    dir_list = []
    for dbtype in dbtype_list:   # 判断是否为文件夹，是的话存入dir_list
        if os.path.isdir(os.path.join(folder_address, dbtype)):
            dir_list.append(dbtype)
    for i in dir_list:  # 遍历文件夹，删除创建时间大于30天的文件
        f_address = folder_address+'/'+i
        file_name = os.listdir(f_address)
        for t in file_name:
            file_address = f_address+'/'+t
            dir_time = get_file_create_time(file_address)
            now = datetime.datetime.now()
            del_time_limit = datetime.timedelta(hours=120)
            if del_time_limit < (now-dir_time):
                os.remove(file_address)


def get_file_create_time(file_address):
    """
    获得文件的创建时间
    """
    file_address = unicode(file_address, 'utf8')
    t = datetime.datetime.fromtimestamp(os.path.getmtime(file_address))
    return t


if __name__ == '__main__':
    schedule.every().day.do(data_clean)
    while True:
        schedule.run_pending()
        time.sleep(600)
