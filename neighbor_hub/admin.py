from django.contrib import admin
from .models import (
    Community,
    NeighborHubProfile,
    Topic,
    Comment,
    TopicLike,
    TopicSubscription,
    Invitation,
    VerificationRequest,
    AppNotification,
)


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'address')


@admin.register(NeighborHubProfile)
class NeighborHubProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'avatar', 'community', 'role', 'building', 'is_verified', 'created_at')
    list_filter = ('role', 'is_verified', 'community')
    search_fields = ('user__username', 'user__phone', 'nickname', 'building')
    readonly_fields = ('user_id', 'user')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'community', 'author', 'category', 'status', 'is_pinned', 'created_at')
    list_filter = ('category', 'status', 'is_pinned', 'community')
    search_fields = ('title', 'content')
    readonly_fields = ('likes_count', 'comments_count', 'views_count')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('topic', 'author', 'content_preview', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('content',)
    
    def content_preview(self, obj):
        return obj.content[:50]
    content_preview.short_description = '内容'


@admin.register(TopicLike)
class TopicLikeAdmin(admin.ModelAdmin):
    list_display = ('topic', 'user', 'created_at')


@admin.register(TopicSubscription)
class TopicSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'user', 'has_update', 'created_at')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('inviter', 'invitee', 'inviter_community', 'status', 'created_at')
    list_filter = ('status', 'inviter_community')


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'community', 'building', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status', 'community')


@admin.register(AppNotification)
class AppNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
