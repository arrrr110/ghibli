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


def get_or_create_user_by_phone(phone, app_name, nickname='', invited_by=None):
    """
    通过手机号获取或创建用户
    同时创建对应应用的 Profile 和 NeighborHubProfile（如果是neighbor_hub应用）
    
    Args:
        phone: 手机号
        app_name: 应用名称
        nickname: 昵称
        invited_by: 邀请人用户ID（可选）
    """
    with transaction.atomic():
        # 查找或创建用户
        user, user_created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'username': f'user_{phone[-8:]}',  # 自动生成用户名
            }
        )
        
        # 确保用户名为 phone 的用户名格式（如果是新创建的）
        if not user.username.startswith('user_'):
            user.username = f'user_{phone[-8:]}'
            user.save(update_fields=['username'])
        
        # 查找或创建 app profile
        profile, profile_created = UserAppProfile.objects.get_or_create(
            user=user,
            app_name=app_name,
        )

        # 如果是neighbor_hub应用，自动创建基础NeighborHubProfile
        neighbor_profile = None
        neighbor_profile_created = False
        if app_name == 'neighbor_hub':
            try:
                from neighbor_hub.models import NeighborHubProfile
                
                # 准备创建参数
                defaults = {
                    'nickname': nickname or f'{phone[:3]}****{phone[-4:]}',
                    'role': NeighborHubProfile.Role.OWNER,
                }
                
                neighbor_profile, neighbor_profile_created = NeighborHubProfile.objects.get_or_create(
                    user=user,
                    defaults=defaults
                )
                
                # 如果是新用户且有邀请人，设置邀请关系
                if (user_created or neighbor_profile_created) and invited_by:
                    try:
                        inviter_user = User.objects.get(id=invited_by)
                        neighbor_profile.invited_by = inviter_user
                        neighbor_profile.save(update_fields=['invited_by'])
                        logger.info(f'为用户 {user.id} 设置邀请人 {invited_by}')
                    except User.DoesNotExist:
                        logger.warning(f'邀请人不存在: {invited_by}')
                        
            except ImportError:
                # 如果neighbor_hub应用不可用，跳过创建
                logger.warning('neighbor_hub应用不可用，跳过创建NeighborHubProfile')
            except Exception as e:
                logger.error(f'创建NeighborHubProfile失败: {e}')
        
        return user, user_created, profile, profile_created, neighbor_profile, neighbor_profile_created


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
        invited_by = serializer.validated_data.get('invited_by')

        # 验证验证码
        success, msg = verify_sms_code(phone, code, purpose='login')
        if not success:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        # 获取或创建用户（get_or_create），传递邀请人信息
        # 优先使用请求体中的invited_by，如果没有则从URL参数中获取
        url_invited_by = request.GET.get('invited_by') if hasattr(request, 'GET') else None
        final_invited_by = invited_by or url_invited_by
        
        user, user_created, profile, profile_created, neighbor_profile, neighbor_profile_created = get_or_create_user_by_phone(
            phone, app_name, invited_by=final_invited_by
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

        # 添加neighbor_hub档案信息（如果是neighbor_hub应用）
        if app_name == 'neighbor_hub' and neighbor_profile:
            response_data['neighbor_hub_profile'] = {
                'id': str(neighbor_profile.id),
                'nickname': neighbor_profile.nickname,
                'is_new_profile': neighbor_profile_created,
                'is_profile_complete': bool(neighbor_profile.community),  # 有小区信息表示档案完整
                'needs_completion': not bool(neighbor_profile.community),  # 需要完善档案
            }

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
