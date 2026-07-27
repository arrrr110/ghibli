import uuid
from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone


class Community(models.Model):
    """小区/社区"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="小区名称")
    address = models.CharField(max_length=255, verbose_name="小区地址")
    description = models.TextField(blank=True, verbose_name="小区描述")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_communities'
    )
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="扩展数据")
    established_at = models.DateField(null=True, blank=True, verbose_name="建成日期")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'neighbor_hub_communities'
        verbose_name = '小区'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.name


class NeighborHubProfile(models.Model):
    """用户在 neighbor_hub 应用中的专属 Profile
    
    职责：存储社区治理相关的用户资料
    - 昵称、头像（应用专属，各应用可不同）
    - 角色、认证状态
    - 小区、楼号
    """
    
    class Role(models.TextChoices):
        OWNER = 'owner', '业主'
        COMMITTEE = 'committee', '业委会'
        PROPERTY = 'property', '物业'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='neighbor_hub_profile'
    )
    
    # 应用专属资料
    nickname = models.CharField(max_length=50, blank=True, verbose_name="昵称")
    avatar = models.URLField(blank=True, verbose_name="头像URL")
    bio = models.CharField(max_length=200, blank=True, verbose_name="个人简介")
    
    # 社区关系
    community = models.ForeignKey(
        Community,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='members',
        verbose_name="所属小区"
    )
    role = models.CharField(
        max_length=20, choices=Role.choices,
        default=Role.OWNER, verbose_name="角色"
    )
    building = models.CharField(max_length=50, blank=True, verbose_name="楼号")
    join_note = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name="加入备注",
        help_text="用户加入小区时填写的备注，供业委会审核参考"
    )
    
    # 认证状态
    is_verified = models.BooleanField(default=False, verbose_name="已认证")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_users'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_note = models.CharField(max_length=255, blank=True)
    
    # 邀请关系
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invitees'
    )
    
    is_active = models.BooleanField(default=True)
    extra_data = models.JSONField(default=dict, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'neighbor_hub_profiles'
        verbose_name = '用户档案'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.nickname or self.user} @ {self.community}"
    
    def verify(self, committee_user, role=None, note=''):
        """业委会认证用户
        
        Args:
            committee_user: 业委会用户
            role: 认证后身份（owner/property），默认 owner
            note: 审核备注
        """
        self.is_verified = True
        self.role = role or self.Role.OWNER
        self.verified_by = committee_user
        self.verified_at = timezone.now()
        self.verification_note = note
        self.save(update_fields=[
            'is_verified', 'role', 'verified_by',
            'verified_at', 'verification_note', 'updated_at',
        ])


class Topic(models.Model):
    """小区治理话题"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '正常'
        CLOSED = 'closed', '已关闭'
        HIDDEN = 'hidden', '已隐藏'
    
    class Category(models.TextChoices):
        FACILITY = 'facility', '设施改造'
        NOTICE = 'notice', '物业通知'
        NEIGHBOR = 'neighbor', '邻里关系'
        ENVIRONMENT = 'environment', '环境治理'
        REPAIR = 'repair', '设施维修'
        HELP = 'help', '邻里互助'
        ANNOUNCEMENT = 'announcement', '业委会公告'
        ACTIVITY = 'activity', '社区活动'
        DISPUTE = 'dispute', '邻里纠纷'
        OTHER = 'other', '其他'
    
    class PosterStyle(models.TextChoices):
        GRADIENT = 'gradient', '渐变'
        EMOJI = 'emoji', '表情'
        MINIMAL = 'minimal', '简约'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='topics')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topics')
    author_building = models.CharField(max_length=50, verbose_name="作者楼号")
    author_role = models.CharField(max_length=20, choices=NeighborHubProfile.Role.choices)
    
    title = models.CharField(max_length=100, blank=True, verbose_name="标题")
    content = models.TextField(blank=True, verbose_name="内容")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)

    has_image = models.BooleanField(default=False)
    poster_style = models.CharField(max_length=10, choices=PosterStyle.choices, default=PosterStyle.MINIMAL)

    # 草稿标记：草稿话题不展示在信息流中
    is_draft = models.BooleanField(default=False, verbose_name="草稿")
    # 业务时间：首次发布时间（草稿创建时为 null，发布时赋值）
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="发布时间")

    # 统计数据
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_pinned = models.BooleanField(default=False, verbose_name="置顶")
    extra_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="最后编辑时间")
    
    class Meta:
        db_table = 'neighbor_hub_topics'
        ordering = ['-is_pinned', '-published_at']
        verbose_name = '话题'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.title or '(草稿)'


class TopicImage(models.Model):
    """话题图片"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name='images'
    )
    image_url = models.URLField(verbose_name="图片访问URL")
    oss_key = models.CharField(max_length=255, verbose_name="OSS对象key")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'neighbor_hub_topic_images'
        ordering = ['sort_order', 'created_at']
        verbose_name = '话题图片'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.image_url


@receiver(pre_delete, sender=TopicImage)
def _topic_image_pre_delete(sender, instance, **kwargs):
    """删除 TopicImage 时同步删除 OSS 上的文件

    使用 pre_delete 信号而非覆盖 delete() 方法，
    确保以下场景都能清理 OSS：
    - 实例 delete() 调用
    - queryset 批量 delete()（如 TopicImage.objects.filter(...).delete()）
    - 话题 CASCADE 级联删除
    """
    from .services.oss_client import delete_oss_object
    if instance.oss_key:
        delete_oss_object(instance.oss_key)


class Comment(models.Model):
    """话题评论"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    author_building = models.CharField(max_length=50)
    author_role = models.CharField(max_length=20, choices=NeighborHubProfile.Role.choices)
    
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True, related_name='replies',
        verbose_name="根评论",
        help_text="回复的根评论（顶级评论），非回复时为 null"
    )
    reply_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='comment_replies',
        verbose_name="回复给",
        help_text="回复的目标用户（扁平化回复模型：parent 指向根评论，reply_to 指向被回复的用户）"
    )
    
    content = models.TextField(max_length=1000)
    likes_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'neighbor_hub_comments'
        ordering = ['-created_at']
        verbose_name = '评论'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.author}: {self.content[:30]}"


class TopicLike(models.Model):
    """话题点赞记录"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topic_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'neighbor_hub_topic_likes'
        unique_together = ['topic', 'user']
        verbose_name = '话题点赞'
        verbose_name_plural = verbose_name


class CommentLike(models.Model):
    """评论点赞记录"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'neighbor_hub_comment_likes'
        unique_together = ['comment', 'user']
        verbose_name = '评论点赞'
        verbose_name_plural = verbose_name


class TopicSubscription(models.Model):
    """话题订阅/收藏记录
    
    用户收藏的话题集中展示在订阅页
    is_pinned 用于用户在收藏夹内个人置顶排序
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='subscriptions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topic_subscriptions')
    has_update = models.BooleanField(default=False)
    
    # 用户个人置顶（仅影响当前用户的收藏列表排序）
    is_pinned = models.BooleanField(default=False, verbose_name="个人置顶")
    pinned_at = models.DateTimeField(null=True, blank=True, verbose_name="置顶时间")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'neighbor_hub_topic_subscriptions'
        unique_together = ['topic', 'user']
        verbose_name = '话题订阅'
        verbose_name_plural = verbose_name
        ordering = ['-is_pinned', '-pinned_at', '-updated_at']


class TopicReadRecord(models.Model):
    """话题阅读记录
    
    每人每话题一条记录，记录阅读次数和最后阅读时间
    用于标记已读/未读状态
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='read_records')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='read_topics')
    read_count = models.PositiveIntegerField(default=1, verbose_name="阅读次数")
    last_read_at = models.DateTimeField(auto_now=True, verbose_name="最后阅读时间")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'neighbor_hub_topic_read_records'
        unique_together = ['topic', 'user']
        verbose_name = '话题阅读'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'last_read_at']),
        ]


class Invitation(models.Model):
    """邀请记录 - 简化版，支持H5分享链接和二维码"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '待接受'
        ACCEPTED = 'accepted', '已接受'
        EXPIRED = 'expired', '已过期'
        CANCELLED = 'cancelled', '已取消'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations'
    )
    inviter_community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='received_invitations'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'neighbor_hub_invitations'
        ordering = ['-created_at']
        verbose_name = '邀请记录'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        invitee_info = self.invitee.username if self.invitee else '未注册'
        return f"{self.inviter.username} -> {invitee_info}"
    
    def accept(self, user):
        """接受邀请"""
        from django.utils import timezone
        if self.status == self.Status.PENDING and self.expires_at > timezone.now():
            self.invitee = user
            self.status = self.Status.ACCEPTED
            self.accepted_at = timezone.now()
            self.save()
            return True
        return False

