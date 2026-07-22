import logging
import uuid
from datetime import timedelta

from django.db.models import Q, Count, Prefetch, Exists, OuterRef, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
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
    TopicReadRecord,
    Invitation,
    VerificationRequest,
    AppNotification,
)
from users.models import UserAppProfile, User
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
    InvitationCreateSerializer,
    VerificationRequestSerializer,
    VerificationRequestReviewSerializer,
    AppNotificationSerializer,
    SwitchCommunitySerializer,
)

logger = logging.getLogger(__name__)


class TopicCursorPagination(CursorPagination):
    """话题列表游标分页
    
    按置顶 + 创建时间倒序游标分页
    每页返回 10 条，前端可通过 cursor 参数加载下一页
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    ordering = ('-is_pinned', '-created_at')


class CurrentUserProfileView(APIView):
    """
    获取/更新当前用户在 neighbor_hub 的 Profile
    GET /api/neighbor-hub/users/me/
    PATCH /api/neighbor-hub/users/me/
    """
    permission_classes = [IsAuthenticated]


class UserProfileLookupView(APIView):
    """
    根据档案ID查询用户档案（用于邀请功能）
    GET /api/neighbor-hub/users/profile/{user_id}/
    
    返回用户的公开信息，用于邀请和展示
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        """
        根据NeighborHubProfile ID获取用户信息
        
        Args:
            user_id: NeighborHubProfile的关联用户UUID
            
        Returns:
            用户的公开档案信息
        """
        try:
            # 查找指定的档案
            profile = NeighborHubProfile.objects.select_related('user', 'community').get(
                user_id=user_id, 
                is_active=True
            )
            
            # 只返回公开信息，过滤敏感数据
            profile_data = {
                'id': str(profile.id),
                'user_id': str(profile.user.id),
                'nickname': profile.nickname or profile.user.username,
                'avatar': profile.avatar,
                'role': profile.role,
                'role_display': profile.get_role_display(),
                'is_verified': profile.is_verified,
                'community': {
                    'id': str(profile.community.id) if profile.community else None,
                    'name': profile.community.name if profile.community else None,
                },
                'building': profile.building,
                'bio': profile.bio,
                'member_since': profile.created_at,
            }
            
            return Response(profile_data)
            
        except NeighborHubProfile.DoesNotExist:
            return Response(
                {'error': '用户档案不存在或已被禁用'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f'查询用户档案失败: {e}')
            return Response(
                {'error': '服务器内部错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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


class SwitchCommunityView(APIView):
    """
    切换当前用户所属小区
    POST /api/neighbor-hub/users/me/community/
    
    规则：
    - 切换到新小区后，用户认证状态自动重置为未认证
    - 用户可自由切换回原小区，需重新认证
    - 小区切换后，用户仅能访问新小区的数据
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = SwitchCommunitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        target_community_id = serializer.validated_data['community']
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        
        if not profile:
            return Response(
                {'error': '用户档案不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查是否切换到同一个小区
        if profile.community and profile.community_id == target_community_id:
            return Response(
                {'error': '您已经是该小区的成员'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取目标小区
        target_community = Community.objects.get(id=target_community_id)
        
        # 记录旧小区信息（用于响应）
        old_community_name = profile.community.name if profile.community else None
        was_verified = profile.is_verified
        old_role = profile.role
        
        # 执行小区切换：重置认证状态
        profile.community = target_community
        profile.is_verified = False
        profile.role = NeighborHubProfile.Role.UNVERIFIED
        profile.verified_by = None
        profile.verified_at = None
        profile.verification_note = ''
        profile.save()
        
        # 返回更新后的 Profile
        response_serializer = NeighborHubProfileSerializer(
            profile, context={'request': request}
        )
        
        return Response({
            'message': '小区切换成功',
            'data': response_serializer.data,
            'meta': {
                'old_community_name': old_community_name,
                'old_community_id': str(profile.community_id) if profile.community else None,
                'was_verified': was_verified,
                'old_role': old_role,
                'new_community_name': target_community.name,
                'requires_reverification': True,
            }
        })


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
        if self.action in ('list', 'retrieve', 'create'):
            return [IsAuthenticated()]
        # 更新/删除小区需要业委会权限
        return [IsAuthenticated(), IsCommitteeMember()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        获取小区成员列表（业委会专用，支持筛选）
        
        查询参数:
        - is_verified: true/false  按认证状态筛选
        - role: owner/committee/property/unverified  按角色筛选
        """
        # 仅业委会可访问
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile or profile.role != 'committee':
            return Response(
                {'error': '仅业委会成员可查看成员列表'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        community = self.get_object()
        queryset = NeighborHubProfile.objects.filter(
            community=community, is_active=True
        ).select_related('user')
        
        # 按认证状态筛选
        is_verified = request.query_params.get('is_verified')
        if is_verified is not None:
            if is_verified.lower() in ('true', '1'):
                queryset = queryset.filter(is_verified=True)
            elif is_verified.lower() in ('false', '0'):
                queryset = queryset.filter(is_verified=False)
        
        # 按角色筛选
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        serializer = NeighborHubProfileSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'], url_path=r'members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """
        业委会删除小区成员（方案A：最小删除）
        
        删除内容：
        1. UserAppProfile - 移除应用访问权
        2. NeighborHubProfile - 软删除（is_active=False，昵称改为已注销）
        
        保留内容：
        - User 基础账户
        - Topic/Comment 等历史数据
        - Invitation 邀请记录
        """
        # 仅业委会可操作
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile or profile.role != 'committee':
            return Response(
                {'error': '仅业委会成员可删除成员'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        community = self.get_object()
        
        # 不能删除自己
        if str(user_id) == str(request.user.id):
            return Response(
                {'error': '不能删除自己'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 查找目标用户
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查目标用户是否是本小区成员
        target_profile = getattr(target_user, 'neighbor_hub_profile', None)
        if not target_profile or not target_profile.is_active:
            return Response(
                {'error': '该用户不是小区活跃成员'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if target_profile.community_id != community.id:
            return Response(
                {'error': '该用户不属于本小区'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 不能删除其他业委会成员
        if target_profile.role == 'committee':
            return Response(
                {'error': '不能删除其他业委会成员'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 1. 删除 UserAppProfile（移除应用访问权）
        UserAppProfile.objects.filter(user=target_user, app_name='neighbor_hub').delete()
        
        # 2. 软删除 NeighborHubProfile
        target_profile.is_active = False
        target_profile.nickname = '已注销用户'
        target_profile.save()
        
        return Response({'message': '成员已从小区移除'}, status=status.HTTP_200_OK)


class TopicViewSet(ModelViewSet):
    """
    话题 CRUD + 互动接口
    GET    /api/neighbor-hub/topics/               列表（自动按用户小区筛选，支持 filter 和游标分页）
    POST   /api/neighbor-hub/topics/               创建话题
    GET    /api/neighbor-hub/topics/{id}/          详情
    PATCH  /api/neighbor-hub/topics/{id}/          更新（作者/业委会）
    POST   /api/neighbor-hub/topics/{id}/like/     点赞/取消点赞
    POST   /api/neighbor-hub/topics/{id}/subscribe/ 订阅/取消订阅
    POST   /api/neighbor-hub/topics/{id}/read/      标记已读
    GET    /api/neighbor-hub/topics/{id}/comments/  评论列表
    POST   /api/neighbor-hub/topics/{id}/comments/  添加评论
    POST   /api/neighbor-hub/topics/{id}/pin/       置顶（业委会）
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    pagination_class = TopicCursorPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TopicListSerializer
        if self.action == 'retrieve':
            return TopicDetailSerializer
        if self.action == 'create':
            return TopicCreateSerializer
        return TopicCreateSerializer
    
    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'neighbor_hub_profile', None)
        
        # 没有小区档案的用户看不到任何话题
        if not profile or not profile.community_id:
            return Topic.objects.none()
        
        # 基础查询：按用户小区筛选
        queryset = Topic.objects.filter(
            community_id=profile.community_id
        ).select_related('community', 'author')
        
        # filter 筛选
        topic_filter = self.request.query_params.get('filter', 'all')
        
        if topic_filter == 'unread':
            # 未读：不存在 TopicReadRecord
            queryset = queryset.filter(
                ~Exists(
                    TopicReadRecord.objects.filter(
                        topic=OuterRef('pk'), user=user
                    )
                )
            )
        elif topic_filter == 'read':
            # 已读：存在 TopicReadRecord
            queryset = queryset.filter(
                Exists(
                    TopicReadRecord.objects.filter(
                        topic=OuterRef('pk'), user=user
                    )
                )
            )
        elif topic_filter == 'liked':
            # 我点赞的
            queryset = queryset.filter(
                Exists(
                    TopicLike.objects.filter(
                        topic=OuterRef('pk'), user=user
                    )
                )
            )
        elif topic_filter == 'subscribed':
            # 我收藏的
            queryset = queryset.filter(
                Exists(
                    TopicSubscription.objects.filter(
                        topic=OuterRef('pk'), user=user
                    )
                )
            )
        
        # 筛选：按分类
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 搜索：标题/内容
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        # 用 Exists 子查询标注当前用户的互动状态
        # Prefetch 预取热评（避免 N+1）
        from django.db.models import Prefetch
        hot_comments_qs = Comment.objects.filter(
            parent__isnull=True, is_active=True
        ).select_related('author').order_by('-likes_count', '-created_at')
        
        queryset = queryset.prefetch_related(
            Prefetch('comments', queryset=hot_comments_qs, to_attr='_hot_comments')
        ).annotate(
            is_liked=Exists(
                TopicLike.objects.filter(topic=OuterRef('pk'), user=user)
            ),
            is_subscribed=Exists(
                TopicSubscription.objects.filter(topic=OuterRef('pk'), user=user)
            ),
            is_read=Exists(
                TopicReadRecord.objects.filter(topic=OuterRef('pk'), user=user)
            ),
            read_count=Coalesce(
                TopicReadRecord.objects.filter(
                    topic=OuterRef('pk'), user=user
                ).values('read_count')[:1],
                0,
                output_field=IntegerField(),
            ),
        )
        
        return queryset
    
    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'comments'):
            return [IsAuthenticated()]
        if self.action == 'create':
            return [IsAuthenticated(), IsVerifiedUser()]
        if self.action == 'pin':
            return [IsAuthenticated(), IsCommitteeMember()]
        if self.action in ('like', 'subscribe', 'read'):
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
    
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """标记话题已读
        
        前端在用户划过话题卡片或进入详情页时调用
        首次标记创建记录，重复调用递增 read_count
        """
        topic = self.get_object()
        record, created = TopicReadRecord.objects.get_or_create(
            topic=topic, user=request.user,
            defaults={'read_count': 1}
        )
        if not created:
            record.read_count += 1
            record.save(update_fields=['read_count'])
        return Response({
            'is_read': True,
            'read_count': record.read_count,
        })
    
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
    邀请管理 - 简化版支持H5分享链接和二维码
    
    GET    /api/neighbor-hub/invitations/             我的邀请记录（作为邀请人）
    POST   /api/neighbor-hub/invitations/             创建邀请记录（前端传入 inviter user_id）
    DELETE /api/neighbor-hub/invitations/{id}/        删除邀请记录
    
    流程:
    1. 前端生成链接: https://域名.com/join?inviter={user_id}
    2. 被邀请用户点击链接注册/登录
    3. 前端检测到 URL 参数 inviter
    4. 前端调用 POST /invitations/ {"inviter": "xxx"} 记录邀请关系
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InvitationCreateSerializer
        return InvitationSerializer
    
    def get_queryset(self):
        """获取当前用户相关的邀请记录（作为邀请人或被邀请人）"""
        return Invitation.objects.filter(
            Q(inviter=self.request.user) | Q(invitee=self.request.user)
        ).select_related('inviter_community', 'invitee', 'inviter')
    
    def create(self, request, *args, **kwargs):
        """创建邀请记录 - 前端传入 inviter（邀请人 user_id）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        inviter_id = serializer.validated_data['inviter']
        
        # 不能邀请自己
        if str(inviter_id) == str(request.user.id):
            return Response(
                {'error': '不能邀请自己'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取邀请人信息
        from users.models import User
        try:
            inviter = User.objects.select_related('neighbor_hub_profile').get(id=inviter_id)
        except User.DoesNotExist:
            return Response(
                {'error': '邀请人不存在'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取邀请人的小区
        inviter_profile = getattr(inviter, 'neighbor_hub_profile', None)
        community = inviter_profile.community if inviter_profile else None
        
        # 创建邀请记录 - 直接设为已接受状态
        invitation = Invitation.objects.create(
            inviter=inviter,
            invitee=request.user,
            inviter_community=community,
            status=Invitation.Status.ACCEPTED,
            accepted_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        response_serializer = InvitationSerializer(invitation, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


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
