import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserAppProfile, LoginRecord
from .serializers import (
    SendSmsCodeSerializer,
    PhoneCodeLoginSerializer,
)
from .signals import user_registered

logger = logging.getLogger(__name__)


def generate_tokens_for_user(user, app_name=''):
    """为用户生成 JWT Token"""
    refresh = RefreshToken.for_user(user)
    
    # 在 token 中加入 app_name 信息
    if app_name:
        refresh['app_name'] = app_name
        refresh.access_token['app_name'] = app_name
    
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'expires_in': int(timedelta(days=36500).total_seconds()),
    }


# ──────────────────────────────────────────────
# 信号返回值收集
# ──────────────────────────────────────────────
# 信号发送后，各接收方可选择返回 {'app_name': ..., 'profile_data': {...}}
# users 只做通用收集和透传，不关心 profile_data 里有什么字段
#

def _collect_app_data(responses):
    """收集信号接收方返回的应用数据，汇总为 {app_name: profile_data}"""
    app_data = {}
    for receiver, response in responses:
        if response and isinstance(response, dict) and 'app_name' in response:
            app_data[response['app_name']] = response.get('profile_data', {})
    return app_data


# ──────────────────────────────────────────────


def get_or_create_user_by_phone(phone, app_name, **kwargs):
    """
    通过手机号获取或创建用户
    同时创建对应应用的 UserAppProfile
    各业务应用的档案通过 user_registered 信号创建，users 不关心谁在监听
    
    Args:
        phone: 手机号
        app_name: 应用名称
        **kwargs: 前端透传的扩展参数，原样转发给信号接收方
                 （如 invited_by, nickname 等，由各应用自行解包校验）
    """
    with transaction.atomic():
        # 查找或创建用户
        user, user_created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'username': f'user_{phone}',  # 用完整手机号避免碰撞
            }
        )
        
        # 注意：不覆写已有用户的 username（如 admin 账户）
        
        # 查找或创建 app profile
        profile, profile_created = UserAppProfile.objects.get_or_create(
            user=user,
            app_name=app_name,
        )

        # 新用户：发送注册信号，由各业务应用监听并创建各自档案
        # 收集各应用返回的 profile 数据，透传给前端
        app_data = {}
        if user_created:
            print(f"\n>>> [users] 手机注册: 准备发送 user_registered 信号")
            print(f"    user={user.id} ({user.username}), app_name={app_name}")
            print(f"    kwargs={kwargs}")
            responses = user_registered.send(
                sender=User,
                user=user,
                app_name=app_name,
                **kwargs,
            )
            app_data = _collect_app_data(responses)
            print(f"<<< [users] 信号发送完毕, app_data={app_data}")
        
        return user, user_created, profile, profile_created, app_data


def verify_sms_code(phone, code, purpose='login'):
    """
    验证手机验证码（调用阿里云 API）
    """
    from .services.aliyun_sms import get_sms_service
    
    sms_service = get_sms_service()
    if not sms_service.is_ready:
        return False, '短信服务未就绪'
    
    success, msg = sms_service.verify_code(phone, code)
    return success, msg


class SendSmsCodeView(APIView):
    """
    发送手机验证码接口
    Browsable API 表单中只需填写：
      - phone: 手机号（必填）
      - purpose: 用途（可选，默认 login）
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = SendSmsCodeSerializer

    def post(self, request):
        import random
        from .services.aliyun_sms import get_sms_service

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data['phone']
        purpose = serializer.validated_data.get('purpose', 'login')

        # 验证码发送由阿里云服务统一管控

        # 使用"##code##"替代，由参数 CodeType 指定验证码生成规则；
        code = "##code##"

        # 调用阿里云短信服务
        sms_service = get_sms_service()
        if not sms_service.is_ready:
            return Response(
                {'error': '短信服务未就绪，请检查 AccessKey 配置'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        success, msg = sms_service.send_verify_code(phone, code)
        if success:
            logger.info(f'短信发送成功: {phone}')
            return Response({'message': '验证码已发送'})
        else:
            logger.error(f'短信发送失败: {phone}, {msg}')
            return Response(
                {'error': f'短信发送失败: {msg}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PhoneLoginView(APIView):
    """
    手机号统一登录接口（登录 + 自动注册）
    Browsable API 表单中需填写：
      - phone: 手机号（必填）
      - code: 验证码（必填）
      - app_name: 应用标识（可选，默认 neighbor_hub）
      - extra: 应用自定义扩展参数（可选，如 {"invited_by": "uuid"}）
      
    功能：如果手机号不存在则自动注册并登录，如果存在则直接登录。
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PhoneCodeLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']
        app_name = serializer.validated_data.get('app_name', '')
        extra = serializer.validated_data.get('extra', {})

        # 验证验证码
        success, msg = verify_sms_code(phone, code, purpose='login')
        if not success:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        user, user_created, profile, profile_created, app_data = get_or_create_user_by_phone(
            phone, app_name, **extra
        )

        # 记录登录
        LoginRecord.objects.create(
            user=user,
            login_type='phone_code',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            app_name=app_name,
        )

        # 生成 Token
        tokens = generate_tokens_for_user(user, app_name)

        response_data = {
            'user': {
                'id': str(user.id),
                'phone': f'{phone[:3]}****{phone[-4:]}',
                'is_new_user': user_created,
            },
            **tokens,
        }

        # 透传各业务应用返回的 profile 数据
        # users 不关心 app_data 里有什么，由各业务应用的信号处理器自行决定
        if app_data:
            response_data['app_data'] = app_data

        # 新用户返回 201，老用户返回 200
        return Response(response_data, status=status.HTTP_201_CREATED if user_created else status.HTTP_200_OK)


class LogoutView(APIView):
    """
    登出接口（将 Refresh Token 加入黑名单）
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_204_NO_CONTENT)

        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': '登出成功'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    获取当前用户信息
    需要 JWT 认证
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': '请先登录'}, status=status.HTTP_401_UNAUTHORIZED)

        user = request.user

        data = {
            'id': str(user.id),
            'username': user.username,
            'phone': f'{user.phone[:3]}****{user.phone[-4:]}' if user.phone else None,
            'email': user.email,
            'date_joined': user.date_joined,
        }

        return Response(data)
