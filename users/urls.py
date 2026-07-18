from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .authentication import (
    send_sms_code,
    phone_login,
    register,
    wechat_login,
    logout_view,
    user_profile,
)

app_name = 'users'

urlpatterns = [
    # 发送验证码
    path('sms/send/', send_sms_code, name='sms-send'),
    
    # 手机号登录
    path('auth/phone-login/', phone_login, name='phone-login'),
    
    # 手机号注册
    path('auth/register/', register, name='register'),
    
    # 微信登录
    path('auth/wechat-login/', wechat_login, name='wechat-login'),
    
    # 登出
    path('auth/logout/', logout_view, name='logout'),
    
    # JWT Token 刷新（使用 simplejwt 默认视图）
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # 获取用户信息
    path('auth/profile/', user_profile, name='user-profile'),
]
