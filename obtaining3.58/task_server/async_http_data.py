# encoding: utf-8
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
import urllib
import json
import time

client = AsyncHTTPClient(max_body_size=10485760000, max_buffer_size=10485760000)  # buffer/body -> 10 G

@gen.coroutine
def async_fetch(url, data_type):
    try:
        res = yield client.fetch(url, request_timeout=300)
    except Exception, e:
        raise gen.Return(("False", str(e)))
    if data_type in ('json', 'JSON'):
        raise gen.Return(('True', json.loads(res.body)))
    else:
        raise gen.Return(('True', res.body))


@gen.coroutine
def async_post(url, json_data, data_type):
    """异步发送数据"""
    try:
        json_data = json.dumps(json_data)
        option = HTTPRequest(url, method="POST", body=json_data, request_timeout=300)
        res = yield client.fetch(option)
    except Exception, e:
        raise gen.Return(("False", str(e)))

    if res.body:  # 不为空，则正常解析
        try:
            if data_type in ('json', 'JSON'):
                raise gen.Return(('True', json.loads(res.body)))
            else:
                raise gen.Return(('True', res.body))
        except Exception, e:
            raise gen.Return(('False', str(e)))
    else: # 否则直接返回错误
        raise gen.Return(('False',res.body))


if __name__ == '__main__':
    d = {
        "time": time.time(),
        "id": "1919810",
        "file_url": "http://cty.design/verify_dns/baidu_8.txt",
        "file_md5": "1abf74b788108aaa5f3ec0aa21ad399e"
        }
    url = "http://localhost:8999/notify/query/domain_list"
    async_post(url, json=d, data_type="json")

