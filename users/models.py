import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    统一用户模型（基础认证）
    
    职责：只负责用户注册、登录认证（手机号/邮箱/用户名+密码）
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
    email = models.EmailField(
        blank=True, 
        null=True, 
        unique=True,
        verbose_name="邮箱",
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        if self.phone:
            return f"{self.phone[:3]}****{self.phone[-4:]}"
        if self.email:
            return self.email
        return self.username or str(self.id)[:8]
    
    def get_app_profile(self, app_name):
        """获取某应用的 Profile"""
        return self.app_profiles.filter(app_name=app_name).first()


class UserAppProfile(models.Model):
    """
    用户在各应用中的应用标记
    
    职责：标记用户注册了哪些应用
    业委会可以删除此记录（禁用用户在应用中的访问）
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
            models.Index(fields=['app_name', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user} @ {self.app_name}"
    
    def deactivate(self):
        """禁用用户在此应用中的访问（软删除）"""
        self.is_active = False
        self.save()
    
    def activate(self):
        """重新激活用户在此应用中的访问"""
        self.is_active = True
        self.save()


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
