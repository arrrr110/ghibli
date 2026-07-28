from django.contrib import admin
from .models import (
    Community,
    NeighborHubProfile,
    Topic,
    TopicImage,
    Comment,
    TopicLike,
    TopicSubscription,
    TopicReadRecord,
    Invitation,
)


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'address')
    list_editable = ('is_active',)


@admin.register(NeighborHubProfile)
class NeighborHubProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'role', 'is_verified', 'avatar', 'community', 'building', 'join_note', 'created_at')
    list_filter = ('role', 'is_verified', 'community')
    search_fields = ('user__username', 'user__phone', 'nickname', 'building')
    readonly_fields = ('user', 'user_id', 'verified_by', 'verified_at', 'last_login_at', 'created_at', 'updated_at')
    ordering = ('-updated_at',)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'community', 'author', 'category', 'status', 'is_draft', 'is_pinned', 'published_at', 'created_at')
    list_filter = ('category', 'status', 'is_draft', 'is_pinned', 'community')
    search_fields = ('title', 'content')
    readonly_fields = ('id', 'likes_count', 'comments_count', 'views_count')


@admin.register(TopicImage)
class TopicImageAdmin(admin.ModelAdmin):
    list_display = ('topic', 'image_url', 'sort_order', 'created_at')
    list_filter = ('topic__community',)
    search_fields = ('topic__title', 'oss_key')
    ordering = ('-created_at',)
    readonly_fields = ('id',)


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
    list_display = ('topic', 'user', 'is_pinned', 'has_update', 'created_at')
    list_filter = ('is_pinned', 'has_update')


@admin.register(TopicReadRecord)
class TopicReadRecordAdmin(admin.ModelAdmin):
    list_display = ('topic', 'user', 'read_count', 'last_read_at')
    search_fields = ('topic__title', 'user__username')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('inviter', 'invitee', 'inviter_community', 'status', 'created_at')
    list_filter = ('status', 'inviter_community')

