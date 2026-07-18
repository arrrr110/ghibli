import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    统一用户模型
    各应用的用户不互通，通过 UserAppProfile 按应用隔离
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        unique=True,
        verbose_name="手机号",
        db_index=True,
    )
    nickname = models.CharField(max_length=50, blank=True, verbose_name="昵称")
    avatar = models.URLField(blank=True, verbose_name="头像URL")
    
    # 用户状态
    is_phone_verified = models.BooleanField(default=False, verbose_name="手机号已验证")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        if self.nickname:
            return self.nickname
        if self.phone:
            return f"{self.phone[:3]}****{self.phone[-4:]}"
        return self.username or str(self.id)[:8]
    
    def get_app_profile(self, app_name):
        """获取某应用的 Profile"""
        return self.app_profiles.filter(app_name=app_name).first()


class UserAppProfile(models.Model):
    """
    用户在各应用中的 Profile
    实现用户按应用隔离
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='app_profiles',
        verbose_name="用户"
    )
    app_name = models.CharField(
        max_length=50, 
        verbose_name="应用标识",
        help_text="应用标识，如: ghibli, neighbor_hub",
        db_index=True,
    )
    
    # 各应用自己的用户标识（如 openid、third_party_id 等）
    app_user_id = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="应用侧用户ID",
        help_text="应用自己体系的用户标识，如微信 openid",
    )
    
    # 用户在应用内的状态
    is_active = models.BooleanField(default=True, verbose_name="在应用中是否激活")
    
    # 应用自定义扩展字段
    extra_data = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name="扩展数据",
        help_text="各应用自定义的用户扩展信息"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'user_app_profiles'
        verbose_name = '用户应用档案'
        verbose_name_plural = verbose_name
        unique_together = ['user', 'app_name']
        indexes = [
            models.Index(fields=['app_name', 'app_user_id']),
        ]
    
    def __str__(self):
        return f"{self.user} @ {self.app_name}"


class VerificationCode(models.Model):
    """
    手机验证码
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(
        max_length=20, 
        verbose_name="手机号",
        db_index=True,
    )
    code = models.CharField(max_length=6, verbose_name="验证码")
    
    # 验证码用途
    PURPOSE_CHOICES = [
        ('register', '注册'),
        ('login', '登录'),
        ('reset_password', '重置密码'),
        ('bind_phone', '绑定手机'),
    ]
    purpose = models.CharField(
        max_length=20, 
        choices=PURPOSE_CHOICES,
        verbose_name="用途"
    )
    
    # 状态
    is_used = models.BooleanField(default=False, verbose_name="已使用")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="使用时间")
    
    # 有效期
    expires_at = models.DateTimeField(verbose_name="过期时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        db_table = 'verification_codes'
        verbose_name = '验证码'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'purpose', 'is_used']),
        ]
    
    def __str__(self):
        return f"{self.phone} - {self.get_purpose_display()}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired


class LoginRecord(models.Model):
    """
    登录记录
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='login_records',
        verbose_name="用户"
    )
    
    LOGIN_TYPE_CHOICES = [
        ('phone_code', '手机验证码'),
        ('wechat_openid', '微信小程序'),
        ('username_password', '账号密码'),
    ]
    login_type = models.CharField(
        max_length=20, 
        choices=LOGIN_TYPE_CHOICES,
        verbose_name="登录方式"
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP地址")
    user_agent = models.CharField(max_length=500, blank=True, verbose_name="User-Agent")
    
    # 应用来源
    app_name = models.CharField(max_length=50, blank=True, verbose_name="登录应用")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登录时间")
    
    class Meta:
        db_table = 'login_records'
        verbose_name = '登录记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.get_login_type_display()} - {self.created_at}"
