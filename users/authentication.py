import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserAppProfile, VerificationCode, LoginRecord
from .serializers import (
    PhoneCodeLoginSerializer,
    RegisterSerializer,
    WechatLoginSerializer,
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
        'expires_in': int(timedelta(minutes=30).total_seconds()),
    }


def get_or_create_user_by_phone(phone, app_name, nickname=''):
    """
    通过手机号获取或创建用户
    同时创建对应应用的 Profile
    """
    # 查找或创建用户
    user, user_created = User.objects.get_or_create(
        phone=phone,
        defaults={
            'username': f'user_{phone[-8:]}',  # 自动生成用户名
            'nickname': nickname or f'用户{phone[-4:]}',
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
        defaults={'app_user_id': phone}
    )
    
    return user, user_created, profile, profile_created


def get_or_create_user_by_openid(openid, app_name, extra_data=None):
    """
    通过微信 openid 获取或创建用户（用于微信小程序等）
    """
    # 尝试通过 app profile 查找
    profile = UserAppProfile.objects.filter(
        app_name=app_name,
        app_user_id=openid
    ).first()
    
    if profile:
        return profile.user, False, profile, False
    
    # 创建新用户
    user = User.objects.create(
        username=f'wx_{openid[-12:]}',
        nickname=extra_data.get('nickname', f'微信用户{openid[-4:]}') if extra_data else f'微信用户{openid[-4:]}',
        is_phone_verified=False,
    )
    
    profile = UserAppProfile.objects.create(
        user=user,
        app_name=app_name,
        app_user_id=openid,
        extra_data=extra_data or {}
    )
    
    return user, True, profile, True


def verify_sms_code(phone, code, purpose='login'):
    """
    验证手机验证码
    """
    try:
        # 查找最近5分钟内、未使用、未过期的验证码
        five_min_ago = timezone.now() - timedelta(minutes=5)
        verification = VerificationCode.objects.filter(
            phone=phone,
            code=code,
            purpose=purpose,
            is_used=False,
            created_at__gte=five_min_ago,
        ).order_by('-created_at').first()
        
        if not verification:
            return False, '验证码无效或已过期'
        
        if verification.is_expired:
            return False, '验证码已过期'
        
        # 标记验证码已使用
        verification.is_used = True
        verification.used_at = timezone.now()
        verification.save(update_fields=['is_used', 'used_at'])
        
        return True, '验证成功'
    except Exception as e:
        logger.error(f'验证码验证失败: {e}')
        return False, '验证失败，请重试'


@api_view(['POST'])
@permission_classes([AllowAny])
def send_sms_code(request):
    """
    发送手机验证码接口
    
    请求体:
    {
        "phone": "13800138000",
        "purpose": "register"  // register / login / reset_password / bind_phone
    }
    
    实际项目中应该调用第三方短信服务，这里先模拟
    """
    phone = request.data.get('phone')
    purpose = request.data.get('purpose', 'login')
    
    if not phone:
        return Response(
            {'error': '请提供手机号'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 简单的手机号格式验证
    if len(phone) != 11 or not phone.isdigit():
        return Response(
            {'error': '手机号格式不正确'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 频率限制：60秒内只能发送一次
    one_min_ago = timezone.now() - timedelta(minutes=1)
    recent_sent = VerificationCode.objects.filter(
        phone=phone,
        purpose=purpose,
        created_at__gte=one_min_ago
    ).exists()
    
    if recent_sent:
        return Response(
            {'error': '请求过于频繁，请稍后再试'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # 生成6位随机验证码
    import random
    code = f'{random.randint(100000, 999999)}'
    
    # 保存到数据库
    expires_at = timezone.now() + timedelta(minutes=10)
    VerificationCode.objects.create(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=expires_at
    )
    
    # TODO: 实际项目中这里调用第三方短信服务发送验证码
    # 例如阿里云 SMS、腾讯云 SMS 等
    # send_sms_via_service(phone, code)
    
    logger.info(f'验证码已发送到 {phone}: {code}')
    
    if True:  # DEBUG模式下返回验证码
        message = '验证码已发送（实际项目中请通过短信发送）'
        response_data = {'message': message}
        if True:  # DEBUG模式
            response_data['debug_code'] = code  # 仅调试用，生产环境必须移除
        return Response(response_data)
    
    return Response({'message': '验证码已发送'})


@api_view(['POST'])
@permission_classes([AllowAny])
def phone_login(request):
    """
    手机号+验证码登录接口
    
    请求体:
    {
        "phone": "13800138000",
        "code": "123456",
        "app_name": "neighbor_hub"
    }
    """
    phone = request.data.get('phone')
    code = request.data.get('code')
    app_name = request.data.get('app_name', '')
    
    if not phone or not code:
        return Response(
            {'error': '请提供手机号和验证码'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 验证验证码
    success, msg = verify_sms_code(phone, code, purpose='login')
    if not success:
        return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
    
    # 获取或创建用户
    user, user_created, profile, profile_created = get_or_create_user_by_phone(phone, app_name)
    
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
    
    return Response({
        'user': {
            'id': str(user.id),
            'nickname': user.nickname,
            'phone': f'{phone[:3]}****{phone[-4:]}',
            'avatar': user.avatar,
            'is_new_user': user_created,
        },
        **tokens,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    手机号注册接口
    
    请求体:
    {
        "phone": "13800138000",
        "code": "123456",
        "nickname": "用户昵称",
        "app_name": "neighbor_hub"
    }
    """
    phone = request.data.get('phone')
    code = request.data.get('code')
    nickname = request.data.get('nickname', '')
    app_name = request.data.get('app_name', '')
    
    if not phone or not code:
        return Response(
            {'error': '请提供手机号和验证码'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 检查是否已注册
    if User.objects.filter(phone=phone).exists():
        return Response(
            {'error': '该手机号已注册'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 验证验证码
    success, msg = verify_sms_code(phone, code, purpose='register')
    if not success:
        return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
    
    # 创建用户
    user, _, profile, _ = get_or_create_user_by_phone(phone, app_name, nickname)
    
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
    
    return Response({
        'user': {
            'id': str(user.id),
            'nickname': user.nickname,
            'phone': f'{phone[:3]}****{phone[-4:]}',
            'avatar': user.avatar,
        },
        **tokens,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_login(request):
    """
    微信登录接口（自动创建用户）
    小程序前端传来 code，后端换 openid 后自动注册/登录
    
    请求体:
    {
        "code": "wx.login返回的code",
        "app_name": "ghibli",
        "extra_data": {"nickname": "", "avatar": ""}  // 可选
    }
    """
    code = request.data.get('code')
    app_name = request.data.get('app_name', '')
    extra_data = request.data.get('extra_data', {})
    
    if not code:
        return Response(
            {'error': '请提供微信 code'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # TODO: 实际项目中，这里应该调用微信接口换取 openid
    # openid = get_wechat_openid(code, WEIXIN_APPID, WEIXIN_APPSECRET)
    
    # 模拟：用 code 生成一个 openid（实际不要这样！）
    import hashlib
    openid = hashlib.md5(f'{code}_{app_name}'.encode()).hexdigest()[:32]
    
    # 获取或创建用户
    user, user_created, profile, profile_created = get_or_create_user_by_openid(
        openid, app_name, extra_data
    )
    
    # 记录登录
    LoginRecord.objects.create(
        user=user,
        login_type='wechat_openid',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        app_name=app_name,
    )
    
    # 生成 Token
    tokens = generate_tokens_for_user(user, app_name)
    
    return Response({
        'user': {
            'id': str(user.id),
            'nickname': user.nickname,
            'avatar': user.avatar,
            'is_new_user': user_created,
        },
        'openid': openid,
        **tokens,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """
    登出接口（将 Refresh Token 加入黑名单）
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework.permissions import IsAuthenticated
    
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


@api_view(['GET'])
def user_profile(request):
    """
    获取当前用户信息
    需要 JWT 认证
    """
    from rest_framework.permissions import IsAuthenticated
    if not request.user.is_authenticated:
        return Response({'error': '请先登录'}, status=status.HTTP_401_UNAUTHORIZED)
    
    user = request.user
    
    # 获取 token 中的 app_name
    app_name = ''
    auth = request.auth
    if auth and isinstance(auth, dict):
        app_name = auth.get('app_name', '')
    
    # 获取应用 Profile
    app_profile = user.get_app_profile(app_name) if app_name else None
    
    data = {
        'id': str(user.id),
        'username': user.username,
        'nickname': user.nickname,
        'phone': f'{user.phone[:3]}****{user.phone[-4:]}' if user.phone else None,
        'avatar': user.avatar,
        'date_joined': user.date_joined,
    }
    
    if app_profile:
        data['app_profile'] = {
            'app_name': app_profile.app_name,
            'extra_data': app_profile.extra_data,
        }
    
    return Response(data)
