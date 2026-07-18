from rest_framework import serializers
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


class CommunitySerializer(serializers.ModelSerializer):
    """小区序列化器"""
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Community
        fields = [
            'id', 'name', 'address', 'description', 'is_active',
            'established_at', 'members_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_members_count(self, obj):
        return obj.members.count()


class NeighborHubProfileSerializer(serializers.ModelSerializer):
    """用户档案序列化器"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    nickname = serializers.CharField(source='user.nickname', read_only=True)
    phone = serializers.SerializerMethodField()
    community_name = serializers.CharField(source='community.name', read_only=True)
    
    class Meta:
        model = NeighborHubProfile
        fields = [
            'id', 'user_id', 'nickname', 'phone',
            'community', 'community_name',
            'role', 'building', 'bio',
            'is_verified', 'verified_at', 'verification_note',
            'invited_by',
            'is_active', 'last_login_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'verified_at', 'verified_by',
            'invited_by', 'last_login_at',
            'created_at', 'updated_at'
        ]
    
    def get_phone(self, obj):
        """手机号脱敏显示"""
        phone = obj.user.phone
        if phone and len(phone) == 11:
            return f"{phone[:3]}****{phone[-4:]}"
        return None
    
    def update(self, instance, validated_data):
        """只允许更新 building, bio 等其他字段不可变"""
        allowed_fields = ['building', 'bio']
        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class CommentSerializer(serializers.ModelSerializer):
    """评论序列化器"""
    author_nickname = serializers.CharField(source='author.nickname', read_only=True)
    author_avatar = serializers.CharField(source='author.avatar', read_only=True)
    author_building = serializers.CharField(read_only=True)
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'topic',
            'author', 'author_nickname', 'author_avatar',
            'author_building', 'author_role',
            'parent', 'content', 'likes_count',
            'is_active', 'replies_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'author', 'author_building', 'author_role',
            'likes_count', 'is_active',
            'created_at', 'updated_at'
        ]
    
    def get_replies_count(self, obj):
        return obj.replies.count()


class TopicListSerializer(serializers.ModelSerializer):
    """话题列表序列化器（精简字段，用于列表接口）"""
    author_nickname = serializers.CharField(source='author.nickname', read_only=True)
    community_name = serializers.CharField(source='community.name', read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = [
            'id', 'community', 'community_name',
            'author', 'author_nickname', 'author_building', 'author_role',
            'title', 'category',
            'has_image', 'image_url', 'poster_style',
            'likes_count', 'comments_count', 'views_count',
            'status', 'is_pinned',
            'is_liked', 'is_subscribed',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'author', 'author_building', 'author_role',
            'likes_count', 'comments_count', 'views_count',
            'status', 'is_pinned',
            'created_at', 'updated_at'
        ]
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.subscriptions.filter(user=request.user).exists()
        return False


class TopicDetailSerializer(TopicListSerializer):
    """话题详情序列化器（包含完整内容）"""
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + ['content', 'extra_data']


class TopicCreateSerializer(serializers.ModelSerializer):
    """创建话题序列化器"""
    
    class Meta:
        model = Topic
        fields = [
            'community', 'title', 'content', 'category',
            'has_image', 'image_url', 'poster_style',
            'extra_data'
        ]
    
    def validate(self, attrs):
        request = self.context.get('request')
        if request:
            # 自动填充作者信息
            attrs['author'] = request.user
            profile = getattr(request.user, 'neighbor_hub_profile', None)
            attrs['author_building'] = profile.building if profile else ''
            attrs['author_role'] = profile.role if profile else 'unverified'
        return attrs


class InvitationSerializer(serializers.ModelSerializer):
    """邀请记录序列化器"""
    inviter_nickname = serializers.CharField(source='inviter.nickname', read_only=True)
    community_name = serializers.CharField(source='inviter_community.name', read_only=True)
    
    class Meta:
        model = Invitation
        fields = [
            'id', 'inviter', 'inviter_nickname',
            'inviter_community', 'community_name',
            'invitee_phone', 'invitee_name',
            'code', 'status', 'expires_at', 'accepted_at',
            'created_at'
        ]
        read_only_fields = [
            'id', 'inviter', 'inviter_community',
            'code', 'status', 'accepted_at', 'created_at'
        ]


class VerificationRequestSerializer(serializers.ModelSerializer):
    """认证申请序列化器"""
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    community_name = serializers.CharField(source='community.name', read_only=True)
    reviewed_by_nickname = serializers.CharField(source='reviewed_by.nickname', read_only=True)
    
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'user', 'user_nickname',
            'community', 'community_name',
            'name', 'phone', 'building',
            'status', 'reviewed_by', 'reviewed_by_nickname',
            'reviewed_at', 'review_note',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'status',
            'reviewed_by', 'reviewed_at', 'review_note',
            'created_at', 'updated_at'
        ]


class VerificationRequestReviewSerializer(serializers.Serializer):
    """认证审核序列化器"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AppNotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    
    class Meta:
        model = AppNotification
        fields = [
            'id', 'type', 'title', 'content',
            'related_id', 'is_read', 'read_at',
            'created_at'
        ]
        read_only_fields = ['id', 'read_at', 'created_at']
