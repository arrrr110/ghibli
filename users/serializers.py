from rest_framework import serializers
from .models import User, UserAppProfile


class UserSerializer(serializers.ModelSerializer):
    """用户基础信息序列化器（只包含认证相关字段）"""
    class Meta:
        model = User
        fields = ['id', 'username', 'phone', 'email', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class SendSmsCodeSerializer(serializers.Serializer):
    """发送短信验证码的请求序列化器"""
    phone = serializers.CharField(max_length=11, help_text='手机号（11位数字）')
    purpose = serializers.ChoiceField(
        choices=['login', 'reset_password', 'bind_phone'],
        default='login',
        help_text='用途：login / reset_password / bind_phone'
    )

    def validate_phone(self, value):
        if len(value) != 11 or not value.isdigit():
            raise serializers.ValidationError('手机号格式不正确')
        return value


class PhoneCodeLoginSerializer(serializers.Serializer):
    """手机号统一登录（登录 + 自动注册）"""
    phone = serializers.CharField(max_length=11, help_text='11位手机号')
    code = serializers.CharField(max_length=4, help_text='4位短信验证码')
    app_name = serializers.CharField(default='neighbor_hub', help_text='应用标识（默认 neighbor_hub）')
    extra = serializers.JSONField(
        required=False,
        default=dict,
        help_text='应用自定义扩展参数，透传给信号处理器（如 {"invited_by": "uuid"}）',
    )

    def validate_phone(self, value):
        if len(value) != 11 or not value.isdigit():
            raise serializers.ValidationError('手机号格式不正确')
        return value

    def validate_extra(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('extra 必须是 JSON 对象')
        return value


class UserAppProfileSerializer(serializers.ModelSerializer):
    """用户应用标记序列化器"""
    class Meta:
        model = UserAppProfile
        fields = ['id', 'app_name', 'is_active', 'extra_data', 'created_at']

