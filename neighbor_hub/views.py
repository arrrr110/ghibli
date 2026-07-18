import uuid
from datetime import timedelta

from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

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
from .permissions import (
    IsVerifiedUser,
    IsCommitteeMember,
    IsCommitteeOrAuthor,
)
from .serializers import (
    CommunitySerializer,
    NeighborHubProfileSerializer,
    TopicListSerializer,
    TopicDetailSerializer,
    TopicCreateSerializer,
    CommentSerializer,
    InvitationSerializer,
    VerificationRequestSerializer,
    VerificationRequestReviewSerializer,
    AppNotificationSerializer,
)


class CurrentUserProfileView(APIView):
    """
    获取/更新当前用户在 neighbor_hub 的 Profile
    GET /api/neighbor-hub/users/me/
    PATCH /api/neighbor-hub/users/me/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile:
            return Response(
                {'error': '用户档案不存在，请先完成注册流程'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = NeighborHubProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    
    def patch(self, request):
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile:
            return Response(
                {'error': '用户档案不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = NeighborHubProfileSerializer(
            profile, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CommunityViewSet(ModelViewSet):
    """
    小区 CRUD
    GET    /api/neighbor-hub/communities/          列表
    POST   /api/neighbor-hub/communities/          创建
    GET    /api/neighbor-hub/communities/{id}/     详情
    PATCH  /api/neighbor-hub/communities/{id}/     更新
    DELETE /api/neighbor-hub/communities/{id}/     删除
    GET    /api/neighbor-hub/communities/{id}/members/  成员列表
    """
    queryset = Community.objects.prefetch_related('members')
    serializer_class = CommunitySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    
    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsCommitteeMember()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """获取小区成员列表"""
        community = self.get_object()
        profiles = NeighborHubProfile.objects.filter(
            community=community, is_active=True
        ).select_related('user')
        serializer = NeighborHubProfileSerializer(profiles, many=True, context={'request': request})
        return Response(serializer.data)


class TopicViewSet(ModelViewSet):
    """
    话题 CRUD + 互动接口
    GET    /api/neighbor-hub/topics/               列表（支持筛选）
    POST   /api/neighbor-hub/topics/               创建话题
    GET    /api/neighbor-hub/topics/{id}/          详情
    PATCH  /api/neighbor-hub/topics/{id}/          更新（作者/业委会）
    POST   /api/neighbor-hub/topics/{id}/like/     点赞/取消点赞
    POST   /api/neighbor-hub/topics/{id}/subscribe/ 订阅/取消订阅
    GET    /api/neighbor-hub/topics/{id}/comments/  评论列表
    POST   /api/neighbor-hub/topics/{id}/comments/  添加评论
    POST   /api/neighbor-hub/topics/{id}/pin/       置顶（业委会）
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TopicListSerializer
        if self.action == 'retrieve':
            return TopicDetailSerializer
        if self.action == 'create':
            return TopicCreateSerializer
        return TopicCreateSerializer
    
    def get_queryset(self):
        queryset = Topic.objects.select_related('community', 'author').prefetch_related(
            'comments', 'likes', 'subscriptions'
        )
        # 筛选：按小区
        community_id = self.request.query_params.get('community')
        if community_id:
            queryset = queryset.filter(community_id=community_id)
        # 筛选：按分类
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        # 筛选：按状态
        status_filter = self.request.query_params.get('status', 'active')
        queryset = queryset.filter(status=status_filter)
        # 搜索：标题/内容
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))
        return queryset
    
    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'comments'):
            return [IsAuthenticated()]
        if self.action == 'create':
            return [IsAuthenticated(), IsVerifiedUser()]
        if self.action == 'pin':
            return [IsAuthenticated(), IsCommitteeMember()]
        if self.action in ('like', 'subscribe'):
            return [IsAuthenticated(), IsVerifiedUser()]
        return [IsAuthenticated(), IsCommitteeOrAuthor()]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """点赞/取消点赞"""
        topic = self.get_object()
        like, created = TopicLike.objects.get_or_create(
            topic=topic, user=request.user
        )
        if not created:
            # 已点赞，取消点赞
            like.delete()
            topic.likes_count = max(0, topic.likes_count - 1)
            topic.save(update_fields=['likes_count'])
            return Response({'liked': False, 'likes_count': topic.likes_count})
        # 新增点赞
        topic.likes_count += 1
        topic.save(update_fields=['likes_count'])
        return Response({'liked': True, 'likes_count': topic.likes_count})
    
    @action(detail=True, methods=['post'])
    def subscribe(self, request, pk=None):
        """订阅/取消订阅"""
        topic = self.get_object()
        sub, created = TopicSubscription.objects.get_or_create(
            topic=topic, user=request.user
        )
        if not created:
            # 已订阅，取消订阅
            sub.delete()
            return Response({'subscribed': False})
        return Response({'subscribed': True})
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """获取评论列表 / 添加评论"""
        topic = self.get_object()
        if request.method == 'GET':
            # 顶级评论
            comments = Comment.objects.filter(
                topic=topic, parent__isnull=True, is_active=True
            ).select_related('author')
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        # POST 添加评论
        content = request.data.get('content', '').strip()
        if not content:
            raise ValidationError({'content': '评论内容不能为空'})
        parent_id = request.data.get('parent')
        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id, topic=topic)
            except Comment.DoesNotExist:
                raise ValidationError({'parent': '父评论不存在'})
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        comment = Comment.objects.create(
            topic=topic,
            author=request.user,
            author_building=profile.building if profile else '',
            author_role=profile.role if profile else 'unverified',
            parent=parent,
            content=content
        )
        topic.comments_count += 1
        topic.save(update_fields=['comments_count'])
        # 通知被回复者
        if parent and parent.author != request.user:
            AppNotification.objects.create(
                user=parent.author,
                type=AppNotification.Type.TOPIC_REPLY,
                title='有人回复了你的评论',
                content=f'{request.user.nickname or request.user.username} 回复了你',
                related_id=str(topic.id)
            )
        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """置顶话题"""
        topic = self.get_object()
        topic.is_pinned = not topic.is_pinned
        topic.save(update_fields=['is_pinned'])
        return Response({'is_pinned': topic.is_pinned})


class InvitationViewSet(ModelViewSet):
    """
    邀请管理
    GET    /api/neighbor-hub/invitations/       我的邀请记录
    POST   /api/neighbor-hub/invitations/       创建邀请
    POST   /api/neighbor-hub/invitations/verify/ 验证邀请码
    """
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Invitation.objects.filter(
            inviter=self.request.user
        ).select_related('inviter_community')
    
    def perform_create(self, serializer):
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expires_at = timezone.now() + timedelta(days=7)
        # 获取用户的社区
        profile = getattr(self.request.user, 'neighbor_hub_profile', None)
        community = profile.community if profile else None
        serializer.save(
            inviter=self.request.user,
            inviter_community=community,
            code=code,
            expires_at=expires_at
        )
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """验证邀请码"""
        code = request.data.get('code', '').strip().upper()
        if not code:
            raise ValidationError({'code': '请输入邀请码'})
        try:
            invitation = Invitation.objects.get(
                code=code,
                status=Invitation.Status.PENDING,
                expires_at__gt=timezone.now()
            )
            return Response({
                'valid': True,
                'community_name': invitation.inviter_community.name,
                'inviter_name': invitation.inviter.nickname or invitation.inviter.username
            })
        except Invitation.DoesNotExist:
            return Response({'valid': False, 'message': '邀请码无效或已过期'})


class VerificationRequestViewSet(ModelViewSet):
    """
    身份认证申请
    POST   /api/neighbor-hub/verification-requests/           提交申请
    GET    /api/neighbor-hub/verification-requests/           查看我的申请
    GET    /api/neighbor-hub/verification-requests/pending/   待审核列表（业委会）
    POST   /api/neighbor-hub/verification-requests/{id}/review/  审核（业委会）
    """
    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'neighbor_hub_profile', None)
        if self.action == 'pending':
            # 业委会查看其小区的待审核列表
            if profile and profile.role == 'committee':
                return VerificationRequest.objects.filter(
                    status=VerificationRequest.Status.PENDING,
                    community=profile.community
                ).select_related('user', 'community')
            return VerificationRequest.objects.none()
        return VerificationRequest.objects.filter(user=user).select_related('community')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """待审核列表"""
        queryset = self.get_queryset()
        serializer = VerificationRequestSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """审核认证申请"""
        verification_request = self.get_object()
        serializer = VerificationRequestReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        note = serializer.validated_data.get('note', '')
        if action == 'approve':
            verification_request.approve(request.user, note)
            # 发送通知给申请者
            AppNotification.objects.create(
                user=verification_request.user,
                type=AppNotification.Type.VERIFICATION,
                title='身份认证已通过',
                content=f'恭喜！您已成为业主',
                related_id=str(verification_request.id)
            )
        else:
            verification_request.status = VerificationRequest.Status.REJECTED
            verification_request.reviewed_by = request.user
            verification_request.reviewed_at = timezone.now()
            verification_request.review_note = note
            verification_request.save()
            AppNotification.objects.create(
                user=verification_request.user,
                type=AppNotification.Type.VERIFICATION,
                title='身份认证被拒绝',
                content=f'原因：{note or "不符合要求"}',
                related_id=str(verification_request.id)
            )
        return Response({'status': verification_request.status})


class NotificationViewSet(ModelViewSet):
    """
    通知管理
    GET  /api/neighbor-hub/notifications/                 通知列表
    GET  /api/neighbor-hub/notifications/unread-count/    未读数量
    POST /api/neighbor-hub/notifications/{id}/read/       标记已读
    POST /api/neighbor-hub/notifications/read-all/        全部已读
    """
    serializer_class = AppNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AppNotification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """获取未读通知数量"""
        count = AppNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """标记单条通知为已读"""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        return Response({'read': True})
    
    @action(detail=False, methods=['post'])
    def read_all(self, request):
        """全部标记为已读"""
        AppNotification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({'message': '已全部标记为已读'})
