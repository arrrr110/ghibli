from rest_framework import serializers
from .models import (
    Community,
    NeighborHubProfile,
    Topic,
    Comment,
    TopicLike,
    TopicSubscription,
    TopicReadRecord,
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
    """用户档案序列化器（neighbor_hub 应用专属）"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    phone = serializers.SerializerMethodField()
    community_name = serializers.CharField(source='community.name', read_only=True)
    
    class Meta:
        model = NeighborHubProfile
        fields = [
            'id', 'user_id', 'nickname', 'avatar', 'phone',
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
        """
        允许更新业务字段，禁止修改系统管理字段（认证、角色、UUID等）
        可按需修改 allowed_fields 来开放/限制字段
        """
        # 用户可以修改的业务字段
        allowed_fields = [
            'nickname',     # 昵称
            'avatar',       # 头像URL  
            'building',     # 楼号
            'bio',          # 个人简介
        ]
        
        # 禁止修改的系统字段（这些字段有特殊业务流程）
        protected_fields = [
            'role',         # 角色：需通过认证申请/管理后台设置
            'is_verified',  # 认证状态：需通过认证流程
            'verified_by',  # 认证人：系统自动设置
            'verified_at',  # 认证时间：系统自动设置
            'verification_note',  # 认证备注：认证流程设置
            'community',    # 小区：需通过专门的小区切换接口
            'invited_by',   # 邀请人：通过邀请流程自动设置
        ]
        
        # 应用字段更新
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


class HotCommentSerializer(serializers.ModelSerializer):
    """热评序列化器（列表页展示3条热门评论）"""
    author_nickname = serializers.CharField(source='author.nickname', read_only=True)
    author_avatar = serializers.CharField(source='author.avatar', read_only=True)
    
    class Meta:
        model = Comment
        fields = [
            'id', 'author', 'author_nickname', 'author_avatar',
            'author_building', 'content', 'likes_count',
            'created_at'
        ]


class TopicListSerializer(serializers.ModelSerializer):
    """话题列表序列化器（精简字段，用于首页卡片展示）"""
    author_nickname = serializers.CharField(source='author.nickname', read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    is_subscribed = serializers.BooleanField(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    read_count = serializers.IntegerField(read_only=True)
    hot_comments = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = [
            'id',
            'author', 'author_nickname', 'author_building', 'author_role',
            'title', 'category',
            'has_image', 'poster_style',
            'likes_count', 'comments_count', 'views_count',
            'is_pinned',
            'is_liked', 'is_subscribed', 'is_read', 'read_count',
            'hot_comments',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
    
    def get_hot_comments(self, obj):
        """获取3条热门评论（按点赞数倒序）
        
        数据来源：views 中 Prefetch 预取的 _hot_comments 属性
        如果没有预取（如详情页），则实时查询
        """
        # 优先使用 Prefetch 预取的数据（列表页，避免 N+1）
        if hasattr(obj, '_hot_comments'):
            comments = obj._hot_comments[:3]
        else:
            # 详情页或其他未预取的场景，实时查询
            comments = Comment.objects.filter(
                topic=obj, parent__isnull=True, is_active=True
            ).select_related('author').order_by('-likes_count', '-created_at')[:3]
        return HotCommentSerializer(comments, many=True).data


class TopicDetailSerializer(TopicListSerializer):
    """话题详情序列化器（包含完整内容和评论树）"""
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
            attrs['author_role'] = profile.role if profile else 'owner'
        return attrs


class InvitationCreateSerializer(serializers.Serializer):
    """创建邀请序列化器 - 前端传入 inviter（邀请人 user_id）"""
    inviter = serializers.UUIDField(required=True, help_text="邀请人 user_id")
    
    def validate_inviter(self, value):
        """验证邀请人是否存在"""
        from users.models import User
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("邀请人不存在")
        return value


class InvitationSerializer(serializers.ModelSerializer):
    """邀请记录序列化器"""
    inviter_nickname = serializers.CharField(source='inviter.nickname', read_only=True)
    community_name = serializers.CharField(source='inviter_community.name', read_only=True)
    
    class Meta:
        model = Invitation
        fields = [
            'id', 'inviter', 'inviter_nickname',
            'inviter_community', 'community_name',
            'invitee', 'status',
            'expires_at', 'accepted_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'inviter_community',
            'invitee', 'status', 'accepted_at', 'created_at'
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


class SwitchCommunitySerializer(serializers.Serializer):
    """小区切换请求序列化器"""
    community = serializers.UUIDField(
        required=True,
        help_text="目标小区 ID"
    )

    def validate_community(self, value):
        """验证目标小区是否存在且激活"""
        try:
            community = Community.objects.get(id=value)
        except Community.DoesNotExist:
            raise serializers.ValidationError('目标小区不存在')
        if not community.is_active:
            raise serializers.ValidationError('目标小区未激活，无法加入')
        return value
