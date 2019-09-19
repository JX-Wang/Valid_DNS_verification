# encoding:utf-8

import time
import MySQLdb
# 以下三行为禁止数据库警告信息
from warnings import filterwarnings
filterwarnings('ignore', category = MySQLdb.Warning)

db_config = {
    # 'host': '10.81.8.131',
    "host": "10.245.146.39",
    'port': 3306,
    'user': 'root',
    'pwd': 'platform',
    'db_name': 'domain_valid_dns',
    'charset': 'utf8'
}

class MySQL(object):
    """对MySQLdb常用函数进行封装的类"""
    
    error_code = ''  # MySQL错误号码

    _instance = None  # 本类的实例
    _conn = None  # 数据库conn
    _cur = None  # 游标

    _TIMEOUT = 20  # 默认超时30秒
    _timecount = 0
        
    def __init__(self, db_config):
        """构造器：根据数据库连接参数，创建MySQL连接"""
        try:
            self._conn = MySQLdb.connect(host=db_config['host'],
                                         port=int(db_config['port']),
                                         user=db_config['user'],
                                         passwd=db_config['pwd'],
                                         db=db_config['db_name'],
                                         charset=db_config['charset'])
        except MySQLdb.Error, e:
            # 如果没有超过预设超时时间，则再次尝试连接，
            if self._timecount < self._TIMEOUT:
                interval = 5
                self._timecount += interval
                time.sleep(interval)
                self.__init__(db_config)  # 重试
            else:
                raise e

        self._cur = self._conn.cursor(cursorclass = MySQLdb.cursors.DictCursor)  # 返回记录中包含字段名称
        self._instance = MySQLdb

    def query(self,sql):
        """执行 SELECT 语句"""
        try:
            self._cur.execute("SET NAMES utf8")
            result = self._cur.execute(sql)  # 结果为查询到的数量
        except MySQLdb.Error, e:
            raise e
        return result

    def update(self,sql):
        """执行 UPDATE 及 DELETE 语句"""
        try:
            self._cur.execute("SET NAMES utf8") 
            result = self._cur.execute(sql)
            self._conn.commit()
        except MySQLdb.Error, e:
            self.error_code = e.args[0]
            print "数据库错误代码:",e.args[0],e.args[1]
            result = False
        return result

    def update_no_commit(self,sql):
        """执行 UPDATE 及 DELETE 语句"""
        try:
            self._cur.execute("SET NAMES utf8")
            result = self._cur.execute(sql)
            # self._conn.commit()
        except MySQLdb.Error, e:
            self.error_code = e.args[0]
            print "数据库错误代码:",e.args[0],e.args[1]
            result = False
        return result

    def update_many(self,sql,args):
        """执行 UPDATE 及 DELETE 语句"""
        try:
            self._cur.execute("SET NAMES utf8")
            result = self._cur.executemany(sql, args)
            self._conn.commit()
        except MySQLdb.Error, e:
            self.error_code = e.args[0]
            print "数据库错误代码:",e.args[0],e.args[1]
            result = False
        return result
        
    def insert(self,sql):
        """执行 INSERT 语句。如主键为自增长int，则返回新生成的ID"""
        try:
            self._cur.execute("SET NAMES utf8")
            self._cur.execute(sql)
            self._conn.commit()
            return self._conn.insert_id()
        except MySQLdb.Error, e:
            self.error_code = e.args[0]
            print e
            return False

    def insert_no_commit(self,sql):
        """执行 INSERT 语句。如主键为自增长int，则返回新生成的ID"""
        try:
            self._cur.execute("SET NAMES utf8")
            self._cur.execute(sql)
            # self._conn.commit()
            return self._conn.insert_id()
        except MySQLdb.Error, e:
            self.error_code = e.args[0]
            print e
            return False

    def truncate(self, sql):
        """
        删除数据库表
        :param sql: 删除语句
        :return: 删除结果
        """
        try:
            result = self._cur.execute(sql)
            self._conn.commit()
        except MySQLdb.Error, e:
            self.error_code = e.args[0]
            result = False
        return result

    def fetch_all_rows(self):
        """获取所有结果"""
        return self._cur.fetchall()
 
    def get_row_count(self):
        """获取结果行数"""
        return self._cur.rowcount
                          
    def commit(self):
        """数据库commit操作"""
        self._conn.commit()
                        
    def rollback(self):
        """数据库回滚操作"""
        self._conn.rollback()
           
    def __del__(self): 
        """释放资源（系统GC自动调用）"""
        try:
            self._cur.close() 
            self._conn.close() 
        except:
            pass
        
    def close(self):
        """关闭数据库连接"""
        self.__del__()


    def clone_table_structure(self,sql):
        """克隆表结构"""
        try:
            self._cur.execute(sql)
            result = True
            self._conn.commit()
        except MySQLdb.Error, e:
            self.error_code = e.args[0]
            print e
            result = False
        return result

if __name__ == '__main__':
    db = MySQL(db_config)
    sql = 'select domain from domain_ns'
    print db.query(sql)