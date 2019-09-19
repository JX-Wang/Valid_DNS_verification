# 获取域名的DNS记录子系统


## 子系统功能简介
通过读取Kafka任务队列中的域名信息，获取域名的DNS记录，目前只支持NS记录的获取。

## 子系统结构

```text
.
├── resolving_domain_dns  # 未验证的域名数据
└── obtaining_domain_dns.py    # 验证后的域名NS数据
```



