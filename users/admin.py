from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserAppProfile, LoginRecord


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'phone', 'email', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'phone', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('联系信息', {
            'fields': ('phone',),
        }),
    )


@admin.register(UserAppProfile)
class UserAppProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'app_name', 'is_active', 'created_at')
    list_filter = ('app_name', 'is_active')
    search_fields = ('user__username', 'user__phone')
@admin.register(LoginRecord)
class LoginRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_type', 'app_name', 'ip_address', 'created_at')
    list_filter = ('login_type', 'app_name')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'login_type', 'ip_address', 'user_agent', 'app_name', 'created_at')
