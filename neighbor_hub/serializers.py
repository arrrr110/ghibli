from rest_framework import serializers
from django.db.models import Prefetch
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
    author_nickname = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    author_building = serializers.CharField(read_only=True)
    replies_count = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'topic',
            'author', 'author_nickname', 'author_avatar',
            'author_building', 'author_role',
            'parent', 'content', 'likes_count',
            'is_active', 'replies_count', 'replies',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'author', 'author_building', 'author_role',
            'likes_count', 'is_active',
            'created_at', 'updated_at'
        ]
    
    def get_author_nickname(self, obj):
        """从 NeighborHubProfile 获取昵称，回退到 username"""
        profile = getattr(obj.author, 'neighbor_hub_profile', None)
        if profile and profile.nickname:
            return profile.nickname
        return obj.author.username
    
    def get_author_avatar(self, obj):
        """从 NeighborHubProfile 获取头像"""
        profile = getattr(obj.author, 'neighbor_hub_profile', None)
        return profile.avatar if profile else ''
    
    def get_replies_count(self, obj):
        # 优先使用预取数据（避免 N+1 查询）
        if hasattr(obj, '_prefetched_objects_cache') and 'replies' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['replies'])
        return obj.replies.count()
    
    def get_replies(self, obj):
        """获取回复列表（仅详情页预取时有数据，列表页返回空数组）"""
        # 优先使用预取数据
        if hasattr(obj, '_prefetched_objects_cache') and 'replies' in obj._prefetched_objects_cache:
            replies = obj._prefetched_objects_cache['replies']
        else:
            # 没有预取时返回空数组（避免 N+1 查询）
            return []
        return CommentSerializer(replies, many=True, context=self.context).data


class HotCommentSerializer(serializers.ModelSerializer):
    """热评序列化器（列表页展示3条热门评论）"""
    author_nickname = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'author', 'author_nickname', 'author_avatar',
            'author_building', 'content', 'likes_count',
            'created_at'
        ]
    
    def get_author_nickname(self, obj):
        profile = getattr(obj.author, 'neighbor_hub_profile', None)
        if profile and profile.nickname:
            return profile.nickname
        return obj.author.username
    
    def get_author_avatar(self, obj):
        profile = getattr(obj.author, 'neighbor_hub_profile', None)
        return profile.avatar if profile else ''


class TopicImageSerializer(serializers.ModelSerializer):
    """话题图片序列化器（用于图片列表展示）"""

    class Meta:
        model = TopicImage
        fields = ['id', 'topic', 'image_url', 'sort_order', 'created_at']
        read_only_fields = ['id', 'topic', 'image_url', 'sort_order', 'created_at']


class TopicImageUploadSerializer(serializers.Serializer):
    """图片上传表单序列化器（仅用于 DRF Browsable API 渲染文件上传表单）

    实际上传逻辑在 views.TopicViewSet.images() 中手动处理，
    此序列化器不参与数据校验，仅让 DRF Browsable API 显示文件选择框。
    """
    image = serializers.FileField(help_text="上传图片文件（≤500KB，支持 jpg/jpeg/png/webp/gif）")


class TopicListSerializer(serializers.ModelSerializer):
    """话题列表序列化器（精简字段，用于首页卡片展示）"""
    author_nickname = serializers.SerializerMethodField()
    is_liked = serializers.BooleanField(read_only=True)
    is_subscribed = serializers.BooleanField(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    read_count = serializers.IntegerField(read_only=True)
    subscriptions_count = serializers.IntegerField(read_only=True)
    readers_count = serializers.IntegerField(read_only=True)
    hot_comments = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            'id',
            'author', 'author_nickname', 'author_building', 'author_role',
            'title', 'category',
            'has_image', 'poster_style',
            'likes_count', 'comments_count', 'views_count',
            'subscriptions_count', 'readers_count',
            'is_pinned',
            'is_liked', 'is_subscribed', 'is_read', 'read_count',
            'hot_comments',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_author_nickname(self, obj):
        """从 NeighborHubProfile 获取昵称，回退到 username"""
        profile = getattr(obj.author, 'neighbor_hub_profile', None)
        if profile and profile.nickname:
            return profile.nickname
        return obj.author.username

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
            ).select_related('author', 'author__neighbor_hub_profile').order_by('-likes_count', '-created_at')[:3]
        return HotCommentSerializer(comments, many=True, context=self.context).data


class TopicDetailSerializer(TopicListSerializer):
    """话题详情序列化器（包含完整内容、评论树和统计数据）

    用于话题详情页，返回：
    - 话题完整内容
    - 图片列表（images）
    - 阅读数（readers_count）、订阅数（subscriptions_count）、点赞数（likes_count）
    - 讨论区：顶级评论列表（含回复树）
    - 当前用户的互动状态（is_liked/is_subscribed/is_read/read_count）
    """
    comments = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + [
            'content', 'extra_data', 'comments', 'images',
        ]

    def get_comments(self, obj):
        """获取顶级评论列表（含回复树）

        数据来源：views 中 Prefetch 预取的 _detail_comments 属性
        每条评论包含 replies 嵌套（回复列表）
        """
        if hasattr(obj, '_detail_comments'):
            comments = obj._detail_comments
        else:
            replies_qs = Comment.objects.filter(
                is_active=True
            ).select_related('author', 'author__neighbor_hub_profile').order_by('created_at')
            comments = Comment.objects.filter(
                topic=obj, parent__isnull=True, is_active=True
            ).select_related(
                'author', 'author__neighbor_hub_profile'
            ).prefetch_related(
                Prefetch('replies', queryset=replies_qs)
            ).order_by('-created_at')
        return CommentSerializer(comments, many=True, context=self.context).data

    def get_images(self, obj):
        """获取话题图片列表（按 sort_order + created_at 排序）"""
        # 优先使用预取数据（避免 N+1）
        if hasattr(obj, '_prefetched_objects_cache') and 'images' in obj._prefetched_objects_cache:
            images = obj._prefetched_objects_cache['images']
        else:
            images = obj.images.all()
        return TopicImageSerializer(images, many=True, context=self.context).data


class TopicCreateSerializer(serializers.ModelSerializer):
    """创建话题序列化器"""

    class Meta:
        model = Topic
        fields = [
            'community', 'title', 'content', 'category',
            'has_image', 'poster_style',
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
    inviter_nickname = serializers.SerializerMethodField()
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
    
    def get_inviter_nickname(self, obj):
        profile = getattr(obj.inviter, 'neighbor_hub_profile', None)
        if profile and profile.nickname:
            return profile.nickname
        return obj.inviter.username


class VerificationRequestSerializer(serializers.ModelSerializer):
    """认证申请序列化器"""
    user_nickname = serializers.SerializerMethodField()
    community_name = serializers.CharField(source='community.name', read_only=True)
    reviewed_by_nickname = serializers.SerializerMethodField()
    
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
    
    def get_user_nickname(self, obj):
        profile = getattr(obj.user, 'neighbor_hub_profile', None)
        if profile and profile.nickname:
            return profile.nickname
        return obj.user.username
    
    def get_reviewed_by_nickname(self, obj):
        if not obj.reviewed_by:
            return None
        profile = getattr(obj.reviewed_by, 'neighbor_hub_profile', None)
        if profile and profile.nickname:
            return profile.nickname
        return obj.reviewed_by.username


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
