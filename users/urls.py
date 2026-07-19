from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .authentication import (
    SendSmsCodeView,
    PhoneLoginView,
    LogoutView,
    UserProfileView,
)

app_name = 'users'

urlpatterns = [
    # 发送验证码
    path('sms/send/', SendSmsCodeView.as_view(), name='sms-send'),
    
    # 手机号统一登录（登录 + 自动注册）
    path('auth/phone-login/', PhoneLoginView.as_view(), name='phone-login'),
    
    # 登出
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    
    # JWT Token 刷新（使用 simplejwt 默认视图）
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # 获取用户信息
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
]
