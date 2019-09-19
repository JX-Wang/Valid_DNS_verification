# encoding: utf-8

"""
从IANA官网上下载Root Zone File数据到本地
"""
import urllib
import os
import commands
from tqdm import tqdm
from Logger import Logger

logger = Logger(file_path='./log') # 日志


class DownloadProgressBar(tqdm):
    """下载数据的显示进度条"""
    last_block = 0

    def update_to(self, block_num=1, block_size=1, total_size=None):
        """
        block_num  : int, optional
            到目前为止传输的块 [default: 1]
        block_size : int, optional
            每个块的大小 (in tqdm units) [default: 1]
        total_size : int, optional
            文件总大小 (in tqdm units). 如果[default: None] 保持不变
        """
        if total_size is not None:
            self.total = total_size
        self.update((block_num - self.last_block) * block_size)
        self.last_block = block_num


def backup_file():
    """备份文件"""
    backup_command = 'cp ./root_zone_data/root.zone ./root_zone_data/backup_root.zone'  # 备份命令
    commands.getstatusoutput(backup_command)  # 备份


def restore_file():
    """恢复文件"""
    backup_command = 'cp ./root_zone_data/backup_root.zone ./root_zone_data/root.zone'  # 备份命令
    commands.getstatusoutput(backup_command)  # 备份


def root_zone_download():
    """文件下载"""
    logger.logger.info( "开始下载Root Zone File")
    # url = 'ftp://rs.internic.net/domain/root.zone'  # ftp远程文件地址
    url = 'http://www.internic.net/domain/root.zone' # http地址
    save_path = os.path.join('./root_zone_data/', 'root.zone')  # 存储路径
    backup_file()  # 首先备份

    t = DownloadProgressBar(unit='B', unit_scale=True, unit_divisor=1024, miniters=1, desc='root.zone')

    try:
        urllib.urlretrieve(url, save_path, t.update_to)
    except Exception as e:
        logger.logger.error("下载失败，原因："+str(e))
        restore_file()  # 下载失败后恢复
        return
    t.close() # 务必关闭
    logger.logger.info("结束下载")


if __name__ == '__main__':
    root_zone_download()