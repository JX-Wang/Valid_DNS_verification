# encoding: utf-8
"""
读取系统配置参数
"""
import ConfigParser


class SystemConfigParse(object):
    def __init__(self, system_file):
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(system_file)

    def read_task_server(self):
        """读取主节点信息"""
        ip = self.cf.get("task_server", "ip")
        port = self.cf.getint("task_server","port")
        return ip, port

    def read_remote_multiple_server(self):
        """读取探测结束消息通知的web服务器地址集合"""
        ip_port = self.cf.get("remote_multiple_server","ip_port")
        servers = []
        for i in ip_port.split(','):
            s = i.split(':')
            servers.append((s[0],s[1]))
        return servers

    def read_task_size(self):
        """读取消息中含有的最大域名数量"""
        size = self.cf.getint("task_size","task_size_threshold")
        return size

    def read_kafka_servers(self):
        """读取Kafka服务器地址"""
        server_address = self.cf.get("confluent_kafka_addr","server_address")
        return server_address

    def read_log_show(self):
        """是否将日志在终端显示"""
        show_terminal = self.cf.getboolean("log_show_terminal","show_terminal")
        return show_terminal

    def read_task_topic_partition_cnt(self):
        """读取任务主题的分区数量"""
        topic_partition_cnt = self.cf.getint("task_topic_partition_cnt","topic_partition_cnt")
        return topic_partition_cnt

    def read_database_config(self):
        database_config = {}
        for name, value in self.cf.items('database_config'):
            database_config[name] = value
        return database_config

    def read_task_type_topic(self):
        """读取消费者需要消费的topic名称"""
        topic_name = self.cf.get("consumer_topic_name", "topic_name")
        return topic_name

    def read_coroutine_num(self):
        """读取协程数量"""
        coroutine_num = self.cf.getint("coroutine", "coroutine_num")
        return coroutine_num


if __name__ == '__main__':
    system_config = SystemConfigParse('./system.conf')
    print system_config.read_task_server()
    print system_config.read_task_size()
    print system_config.read_kafka_servers()
    print system_config.read_remote_multiple_server()
    print system_config.read_log_show()
    print system_config.read_task_topic_partition_cnt()
    print system_config.read_database_config()
    print system_config.read_task_type_topic()
    print system_config.read_coroutine_num()
