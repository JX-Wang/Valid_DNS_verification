#encoding:utf-8
"""
判断IP地址是否合规
"""
import re

def judge_legal_ip(ip):
    """判断一个IP地址是否合法"""
    compile_ip = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if compile_ip.match(ip):
        return True
    else:
        return False