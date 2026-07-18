from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserAppProfile, VerificationCode, LoginRecord


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'nickname', 'phone', 'is_phone_verified', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_phone_verified', 'is_staff', 'date_joined')
    search_fields = ('username', 'nickname', 'phone')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {
            'fields': ('phone', 'nickname', 'avatar', 'is_phone_verified'),
        }),
    )


@admin.register(UserAppProfile)
class UserAppProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'app_name', 'app_user_id', 'is_active', 'created_at')
    list_filter = ('app_name', 'is_active')
    search_fields = ('user__username', 'user__nickname', 'app_user_id')


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'purpose', 'is_used', 'expires_at', 'created_at')
    list_filter = ('purpose', 'is_used')
    search_fields = ('phone',)


@admin.register(LoginRecord)
class LoginRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_type', 'app_name', 'ip_address', 'created_at')
    list_filter = ('login_type', 'app_name')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'login_type', 'ip_address', 'user_agent', 'app_name', 'created_at')
