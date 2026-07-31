"""
users 应用的自定义信号

设计目的：解耦 users 应用与各业务应用（如 neighbor_hub）
- users 应用在用户注册成功后发送 user_registered 信号
- 各业务应用监听此信号，自行创建各自的应用档案
- users 应用无需知道有哪些业务应用在监听
"""
from django.dispatch import Signal

# 用户注册成功信号
# 固定参数：
#   user: User 实例
#   app_name: 注册来源应用标识（如 'neighbor_hub', 'ghibli'）
# 其余 **kwargs 由前端透传，各接收应用自行解包所需字段
user_registered = Signal()
