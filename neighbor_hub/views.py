import logging
import uuid
from datetime import timedelta

from django.db.models import Q, Count, Prefetch, Exists, OuterRef, IntegerField, Subquery, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.viewsets import ModelViewSet

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
    TopicImageSerializer,
    TopicImageUploadSerializer,
    AvatarUploadSerializer,
    CommentSerializer,
    InvitationSerializer,
    InvitationCreateSerializer,
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
    ordering = ('-is_pinned', '-published_at')


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
        data = serializer.data
        # 附带当前用户创建的小区列表（含未激活，用于中转站/等待审核页减少额外请求）
        my_communities = Community.objects.filter(
            created_by=request.user
        ).annotate(
            members_count=Count('members')
        ).order_by('-created_at')
        data['my_communities'] = CommunitySerializer(
            my_communities, many=True, context={'request': request}
        ).data
        return Response(data)
    
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


class UserStatsView(APIView):
    """
    获取当前用户的聚合统计数据
    GET /api/neighbor-hub/users/me/stats/

    用于个人中心页展示统计数字，避免前端拉取话题列表做计数。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'topics_count': Topic.objects.filter(
                author=user, is_draft=False
            ).count(),
            'subscriptions_count': TopicSubscription.objects.filter(
                user=user
            ).count(),
            'liked_count': TopicLike.objects.filter(
                user=user
            ).count(),
            'read_count': TopicReadRecord.objects.filter(
                user=user
            ).count(),
        })


class AvatarUploadView(GenericAPIView):
    """
    上传用户头像
    POST /api/neighbor-hub/users/me/avatar/
    """
    serializer_class = AvatarUploadSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get('avatar')
        if not file_obj:
            return Response(
                {'avatar': '请选择要上传的图片'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 校验图片大小和格式
        from .services.oss_client import validate_image, upload_avatar, delete_oss_object_by_url
        ext, error = validate_image(file_obj)
        if error:
            return Response(
                {'avatar': error},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile:
            return Response(
                {'error': '用户档案不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 删除旧头像（如果有）
        if profile.avatar:
            delete_oss_object_by_url(profile.avatar)

        # 上传新头像
        try:
            result = upload_avatar(str(request.user.id), file_obj)
        except Exception as e:
            logger.error(f'头像上传失败: {e}')
            return Response(
                {'error': '头像上传失败，请稍后重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 更新 profile
        profile.avatar = result['image_url']
        profile.save(update_fields=['avatar'])

        return Response({
            'avatar': result['image_url'],
            'message': '头像更新成功',
        }, status=status.HTTP_200_OK)


class SwitchCommunityView(APIView):
    """
    切换/退出当前用户所属小区
    POST /api/neighbor-hub/users/me/switch-community/
    
    规则：
    - 传入 community UUID → 切换/加入该小区，重置认证状态
    - 不传 community 或传 null → 退出当前小区，回到中转站
    - 切换/退出后认证状态自动重置为未认证
    - 退出后用户回到中转站，可重新选择小区
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = SwitchCommunitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        target_community_id = serializer.validated_data.get('community')
        join_note = serializer.validated_data.get('join_note', '')
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        
        if not profile:
            return Response(
                {'error': '用户档案不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 记录旧小区信息（用于响应）
        old_community_name = profile.community.name if profile.community else None
        was_verified = profile.is_verified
        old_role = profile.role
        
        if target_community_id is None:
            # 退出当前小区，回到中转站
            if not profile.community:
                return Response(
                    {'error': '您当前不在任何小区中'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            profile.community = None
            profile.is_verified = False
            profile.role = NeighborHubProfile.Role.OWNER
            profile.verified_by = None
            profile.verified_at = None
            profile.verification_note = ''
            profile.join_note = ''
            profile.building = ''
            profile.save()
            
            response_serializer = NeighborHubProfileSerializer(
                profile, context={'request': request}
            )
            return Response({
                'message': '已退出小区，回到中转站',
                'data': response_serializer.data,
                'meta': {
                    'old_community_name': old_community_name,
                    'was_verified': was_verified,
                    'old_role': old_role,
                    'new_community_name': None,
                    'requires_reverification': True,
                }
            })
        
        # 切换到目标小区
        # 检查是否切换到同一个小区
        if profile.community and profile.community_id == target_community_id:
            return Response(
                {'error': '您已经是该小区的成员'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取目标小区
        target_community = Community.objects.get(id=target_community_id)
        
        # 执行小区切换：重置认证状态
        profile.community = target_community
        profile.is_verified = False
        profile.role = NeighborHubProfile.Role.OWNER
        profile.verified_by = None
        profile.verified_at = None
        profile.verification_note = ''
        profile.join_note = join_note
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
    GET    /api/neighbor-hub/communities/          列表（仅已激活小区；?mine=1 查看自己创建的含未激活）
    POST   /api/neighbor-hub/communities/          创建（非管理员创建的小区 is_active=False，待 admin 审核）
    GET    /api/neighbor-hub/communities/{id}/     详情
    PATCH  /api/neighbor-hub/communities/{id}/     更新
    DELETE /api/neighbor-hub/communities/{id}/     删除
    GET    /api/neighbor-hub/communities/{id}/members/  成员列表
    """
    serializer_class = CommunitySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    
    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'create'):
            return [IsAuthenticated()]
        # 更新/删除小区需要业委会权限
        return [IsAuthenticated(), IsCommitteeMember()]
    
    def get_queryset(self):
        queryset = Community.objects.select_related('created_by').annotate(
            members_count=Count('members')
        )
        user = self.request.user
        
        if self.action == 'list':
            # ?mine=1 查看自己创建的小区（含未激活，用于查看审核进度）
            mine = self.request.query_params.get('mine')
            if mine and mine.lower() in ('1', 'true'):
                queryset = queryset.filter(created_by=user)
            elif not user.is_staff:
                # 普通用户只能看到已激活的小区
                queryset = queryset.filter(is_active=True)
            # is_staff 可以看到所有小区
        
        elif self.action == 'retrieve':
            # 详情页：允许查看已激活的、自己创建的、或 staff
            if not user.is_staff:
                queryset = queryset.filter(
                    Q(is_active=True) | Q(created_by=user)
                )
        else:
            # 管理类 action（members/verify_member/remove_member/kick_member/update/destroy）：
            # 业委会只能操作自己所属的小区，防止跨小区越权
            profile = getattr(user, 'neighbor_hub_profile', None)
            if profile and profile.community_id:
                queryset = queryset.filter(id=profile.community_id)
            else:
                queryset = queryset.none()

        return queryset
    
    def perform_create(self, serializer):
        """创建小区：非管理员创建的小区默认未激活，待 admin 审核后激活"""
        is_active = self.request.user.is_staff
        serializer.save(
            created_by=self.request.user,
            is_active=is_active
        )
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        获取小区成员列表（业委会专用，支持筛选）
        
        查询参数:
        - is_verified: true/false  按认证状态筛选
        - role: owner/committee/property  按角色筛选
        """
        community = self.get_object()
        queryset = NeighborHubProfile.objects.filter(
            community=community, is_active=True
        ).exclude(
            role='committee'  # 业委会成员由平台管理员审核，不出现在成员管理列表中
        ).select_related('user', 'invited_by__neighbor_hub_profile')
        
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

    @action(detail=True, methods=['post'], url_path=r'members/(?P<user_id>[^/.]+)/verify')
    def verify_member(self, request, pk=None, user_id=None):
        """业委会认证用户（通过审核）

        POST /api/neighbor-hub/communities/{id}/members/{user_id}/verify/

        将未认证用户设为已认证状态，与 unverify 互为逆操作。

        请求体:
        {
          "role": "owner",       // 认证身份：owner(业主) 或 property(物业)，默认 owner
          "note": "审核备注"
        }
        """
        community = self.get_object()

        # 查找目标用户
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

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

        if target_profile.is_verified:
            return Response(
                {'error': '该用户已认证，无需重复认证'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 不能认证其他业委会成员
        if target_profile.role == 'committee':
            return Response(
                {'error': '不能认证其他业委会成员'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 解析请求参数
        role = request.data.get('role', 'owner')
        if role not in ('owner', 'property'):
            return Response(
                {'error': 'role 只能是 owner 或 property'},
                status=status.HTTP_400_BAD_REQUEST
            )
        note = request.data.get('note', '')

        # 认证用户
        target_profile.verify(request.user, role=role, note=note)

        return Response({'message': '已认证该成员'})

    @action(detail=True, methods=['post'], url_path=r'members/(?P<user_id>[^/.]+)/unverify')
    def unverify_member(self, request, pk=None, user_id=None):
        """业委会取消用户认证（改回待审核状态）
        
        POST /api/neighbor-hub/communities/{id}/members/{user_id}/unverify/
        
        将已认证用户改回未认证状态，用户需重新提交认证申请。
        """
        community = self.get_object()
        
        # 查找目标用户
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
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
        
        if not target_profile.is_verified:
            return Response(
                {'error': '该用户未认证，无需取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 不能取消其他业委会成员的认证
        if target_profile.role == 'committee':
            return Response(
                {'error': '不能取消其他业委会成员的认证'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 取消认证
        target_profile.is_verified = False
        target_profile.role = NeighborHubProfile.Role.OWNER
        target_profile.verified_by = None
        target_profile.verified_at = None
        target_profile.verification_note = ''
        target_profile.save(update_fields=[
            'is_verified', 'role', 'verified_by',
            'verified_at', 'verification_note',
        ])
        
        return Response({'message': '已取消用户认证'})

    @action(detail=True, methods=['post'], url_path=r'members/(?P<user_id>[^/.]+)/kick')
    def kick_member(self, request, pk=None, user_id=None):
        """业委会踢出用户（保留账号活跃，可加入其他小区）
        
        POST /api/neighbor-hub/communities/{id}/members/{user_id}/kick/
        
        与 DELETE（软删除）的区别：
        - kick：community=null, is_verified=false, role=owner, is_active=true
          → 用户可重新选择其他小区并提交认证申请
        - delete：is_active=false, nickname='已注销用户'
          → 用户账号被软删除，无法再使用
        
        用于审核人员拒绝待审核用户。
        """
        community = self.get_object()
        
        # 不能踢自己
        if str(user_id) == str(request.user.id):
            return Response(
                {'error': '不能踢出自己'},
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
        
        # 不能踢其他业委会成员
        if target_profile.role == 'committee':
            return Response(
                {'error': '不能踢出其他业委会成员'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 踢出：保留账号活跃，清除小区关联和认证状态
        target_profile.community = None
        target_profile.is_verified = False
        target_profile.role = NeighborHubProfile.Role.OWNER
        target_profile.verified_by = None
        target_profile.verified_at = None
        target_profile.verification_note = ''
        target_profile.building = ''
        target_profile.save(update_fields=[
            'community', 'is_verified', 'role',
            'verified_by', 'verified_at', 'verification_note',
            'building',
        ])
        
        return Response({'message': f'已将用户移出{community.name}'})


class TopicViewSet(ModelViewSet):
    """
    话题 CRUD + 互动接口 + 图片上传
    GET    /api/neighbor-hub/topics/               列表（自动按用户小区筛选，排除草稿）
    POST   /api/neighbor-hub/topics/               创建话题（直接发布，无需草稿）
    POST   /api/neighbor-hub/topics/draft/         获取或创建草稿话题
    GET    /api/neighbor-hub/topics/{id}/          详情
    PATCH  /api/neighbor-hub/topics/{id}/          更新（作者/业委会）
    POST   /api/neighbor-hub/topics/{id}/publish/  发布草稿话题
    GET    /api/neighbor-hub/topics/{id}/images/   获取图片列表
    POST   /api/neighbor-hub/topics/{id}/images/   上传图片（multipart，≤500KB）
    DELETE /api/neighbor-hub/topics/{id}/images/{image_id}/  删除图片
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
        if self.action == 'images':
            # GET 用图片列表序列化器，POST 用上传表单序列化器（让 DRF 页面渲染文件选择框）
            if self.request.method == 'GET':
                return TopicImageSerializer
            return TopicImageUploadSerializer
        return TopicCreateSerializer
    
    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'neighbor_hub_profile', None)
        
        # 没有小区档案的用户看不到任何话题
        if not profile or not profile.community_id:
            return Topic.objects.none()
        
        # 基础查询：按用户小区筛选，预取作者档案（nickname/avatar 在 NeighborHubProfile 上）
        queryset = Topic.objects.filter(
            community_id=profile.community_id
        ).select_related('community', 'author', 'author__neighbor_hub_profile')

        # 列表页：排除草稿，按 status 参数过滤
        if self.action == 'list':
            queryset = queryset.filter(is_draft=False)
            
            # status 参数：默认 active，业委会可查 hidden/closed/all
            status_param = self.request.query_params.get('status', 'active')
            
            if status_param == 'active':
                queryset = queryset.filter(status=Topic.Status.ACTIVE)
            else:
                # status=all|hidden|closed → 仅业委会可用
                if not profile or profile.role != 'committee':
                    raise PermissionDenied('仅业委会可查看非正常状态的话题')
                
                if status_param == 'hidden':
                    queryset = queryset.filter(status=Topic.Status.HIDDEN)
                elif status_param == 'closed':
                    queryset = queryset.filter(status=Topic.Status.CLOSED)
                # status=all → 不加额外过滤，返回所有状态

        # 列表页才应用筛选条件（详情页直接按 pk 查询，不受列表筛选影响）
        if self.action == 'list':
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
            elif topic_filter == 'mine':
                # 我发起的
                queryset = queryset.filter(author=user)
            
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
        
        # 通用标注：当前用户的互动状态 + 统计数据
        # 注意：Count 必须用 Subquery 包裹，避免多表 JOIN 导致笛卡尔积
        queryset = queryset.annotate(
            is_liked=Exists(
                TopicLike.objects.filter(topic=OuterRef('pk'), user=user)
            ),
            is_subscribed=Exists(
                TopicSubscription.objects.filter(topic=OuterRef('pk'), user=user)
            ),
            is_read=Exists(
                TopicReadRecord.objects.filter(topic=OuterRef('pk'), user=user)
            ),
            # 封面图：第一张图片的 URL（按 sort_order + created_at 排序）
            cover_image=Subquery(
                TopicImage.objects.filter(
                    topic=OuterRef('pk')
                ).order_by('sort_order', 'created_at').values('image_url')[:1]
            ),
            # 当前用户的个人阅读次数（0=未读）
            read_count=Coalesce(
                Subquery(
                    TopicReadRecord.objects.filter(
                        topic=OuterRef('pk'), user=user
                    ).values('read_count')[:1]
                ),
                0,
                output_field=IntegerField(),
            ),
            # 订阅数（总订阅人数）
            subscriptions_count=Coalesce(
                Subquery(
                    TopicSubscription.objects.filter(topic=OuterRef('pk'))
                    .order_by().values('topic')
                    .annotate(c=Count('id')).values('c')
                ),
                0,
                output_field=IntegerField(),
            ),
            # 阅读数（总阅读人数）
            readers_count=Coalesce(
                Subquery(
                    TopicReadRecord.objects.filter(topic=OuterRef('pk'))
                    .order_by().values('topic')
                    .annotate(c=Count('id')).values('c')
                ),
                0,
                output_field=IntegerField(),
            ),
        )
        
        # 详情页预取图片（避免 N+1）
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('images')

        # 预取评论数据（列表页和详情页策略不同）
        if self.action == 'list':
            # 列表页：预取热评（避免 N+1）
            hot_comments_qs = Comment.objects.filter(
                parent__isnull=True, is_active=True
            ).select_related(
                'author', 'author__neighbor_hub_profile'
            ).order_by('-likes_count', '-created_at')
            queryset = queryset.prefetch_related(
                Prefetch('comments', queryset=hot_comments_qs, to_attr='_hot_comments')
            )
        elif self.action == 'retrieve':
            # 详情页：预取顶级评论（含回复），用于讨论区展示
            replies_qs = Comment.objects.filter(
                is_active=True
            ).select_related(
                'author', 'author__neighbor_hub_profile',
                'reply_to', 'reply_to__neighbor_hub_profile',
            ).order_by('created_at')
            top_comments_qs = Comment.objects.filter(
                parent__isnull=True, is_active=True
            ).select_related(
                'author', 'author__neighbor_hub_profile'
            ).order_by('-created_at').prefetch_related(
                Prefetch('replies', queryset=replies_qs)
            )
            queryset = queryset.prefetch_related(
                Prefetch('comments', queryset=top_comments_qs, to_attr='_detail_comments')
            )
        
        return queryset
    
    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'comments', 'images', 'draft', 'publish', 'delete_image'):
            return [IsAuthenticated()]
        if self.action == 'create':
            return [IsAuthenticated(), IsVerifiedUser()]
        if self.action in ('pin', 'hide', 'close'):
            return [IsAuthenticated(), IsCommitteeMember()]
        if self.action in ('like', 'subscribe', 'read'):
            return [IsAuthenticated(), IsVerifiedUser()]
        # update, partial_update, destroy → 作者或业委会
        return [IsAuthenticated(), IsCommitteeOrAuthor()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """编辑话题时手动设置 updated_at（auto_now 已移除）
        
        已关闭/已隐藏的话题不可编辑。
        """
        topic = serializer.instance
        if topic.status != Topic.Status.ACTIVE:
            raise ValidationError({'error': '该话题已关闭或已隐藏，不可编辑'})
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        """删除话题时级联删除所有关联图片（CASCADE + pre_delete 信号自动清理 OSS）
        
        已关闭/已隐藏的话题不可删除。
        """
        if instance.status != Topic.Status.ACTIVE:
            raise ValidationError({'error': '该话题已关闭或已隐藏，不可删除'})
        instance.delete()

    @action(detail=False, methods=['post'])
    def draft(self, request):
        """获取或创建草稿话题

        前端进入「创建话题」页面时调用：
        - 如果当前用户在当前小区已有草稿，返回该草稿（含已上传图片）
        - 如果没有草稿，创建一个新的草稿话题并返回

        响应 (HTTP 200):
        {
          "id": "uuid",
          "is_draft": true,
          "title": "",
          "content": "",
          "category": "other",
          "has_image": false,
          "images": [],
          "created_at": "...",
          "updated_at": "..."
        }
        """
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile or not profile.community_id:
            return Response(
                {'error': '请先加入小区'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 查找当前用户在当前小区的草稿
        draft = Topic.objects.filter(
            author=request.user,
            community_id=profile.community_id,
            is_draft=True
        ).first()

        if not draft:
            # 创建新草稿
            draft = Topic.objects.create(
                author=request.user,
                community_id=profile.community_id,
                author_building=profile.building,
                author_role=profile.role,
                title='',
                content='',
                is_draft=True,
            )

        # 返回草稿信息 + 已有图片
        images = TopicImage.objects.filter(topic=draft).order_by('sort_order', 'created_at')
        return Response({
            'id': str(draft.id),
            'is_draft': True,
            'title': draft.title,
            'content': draft.content,
            'category': draft.category,
            'has_image': draft.has_image,
            'poster_style': draft.poster_style,
            'images': TopicImageSerializer(images, many=True, context={'request': request}).data,
            'created_at': draft.created_at,
            'updated_at': draft.updated_at,
        })

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """发布草稿话题

        将草稿话题转为正式话题（is_draft=False），加入信息流。
        校验：标题 ≥ 2字符，内容非空。

        请求体（可选，如果前端已通过 PATCH 更新过则可不传）:
        {
          "title": "话题标题",
          "content": "话题内容",
          "category": "environment"
        }

        响应 (HTTP 200): 发布后的话题详情
        """
        topic = self.get_object()

        # 仅话题作者可发布
        if topic.author != request.user:
            return Response(
                {'error': '仅话题作者可发布'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not topic.is_draft:
            return Response(
                {'error': '该话题不是草稿，无需发布'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 如果请求体中有 title/content，则更新
        title = request.data.get('title', topic.title).strip()
        content = request.data.get('content', topic.content).strip()
        category = request.data.get('category', topic.category)

        # 校验标题和内容
        if len(title) < 2:
            return Response(
                {'title': '标题至少需要2个字符'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not content:
            return Response(
                {'content': '内容不能为空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        topic.title = title
        topic.content = content
        topic.category = category
        topic.is_draft = False
        # 首次发布时设置 published_at（业务时间），不动 updated_at
        topic.published_at = timezone.now()
        topic.save(update_fields=[
            'title', 'content', 'category',
            'is_draft', 'published_at',
        ])

        serializer = TopicDetailSerializer(topic, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def images(self, request, pk=None):
        """获取图片列表 / 上传图片

        GET  /topics/{id}/images/  → 获取话题的所有图片
        POST /topics/{id}/images/  → 上传单张图片（multipart/form-data）

        上传约束:
        - 单张图片 ≤ 500KB
        - 允许格式: jpg/jpeg/png/webp/gif
        - 每话题最多 9 张图片
        - 仅话题作者可上传
        """
        topic = self.get_object()

        if request.method == 'GET':
            images = TopicImage.objects.filter(topic=topic).order_by('sort_order', 'created_at')
            serializer = TopicImageSerializer(images, many=True, context={'request': request})
            return Response(serializer.data)

        # POST 上传图片
        # 权限校验：仅话题作者可上传
        if topic.author != request.user:
            return Response(
                {'error': '仅话题作者可上传图片'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 获取上传的文件
        file_obj = request.FILES.get('image')
        if not file_obj:
            return Response(
                {'image': '请选择要上传的图片'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 校验图片数量
        from django.conf import settings
        current_count = TopicImage.objects.filter(topic=topic).count()
        if current_count >= settings.MAX_IMAGES_PER_TOPIC:
            return Response(
                {'error': f'该话题已有 {current_count} 张图片，最多 {settings.MAX_IMAGES_PER_TOPIC} 张'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 校验图片大小和格式
        from .services.oss_client import validate_image, upload_topic_image
        ext, error = validate_image(file_obj)
        if error:
            return Response(
                {'image': error},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 上传到 OSS
        try:
            result = upload_topic_image(str(topic.id), file_obj)
        except Exception as e:
            logger.error(f'图片上传失败: {e}')
            return Response(
                {'error': '图片上传失败，请稍后重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 创建 DB 记录
        image = TopicImage.objects.create(
            topic=topic,
            image_url=result['image_url'],
            oss_key=result['oss_key'],
            sort_order=current_count,
        )

        # 更新话题的 has_image 标记
        if not topic.has_image:
            topic.has_image = True
            topic.save(update_fields=['has_image'])

        serializer = TopicImageSerializer(image, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'images/(?P<image_id>[^/.]+)')
    def delete_image(self, request, pk=None, image_id=None):
        """删除单张图片

        DELETE /topics/{id}/images/{image_id}/

        同步删除 OSS 上的文件和 DB 记录。
        仅话题作者可删除。
        """
        topic = self.get_object()

        # 权限校验：仅话题作者可删除
        if topic.author != request.user:
            return Response(
                {'error': '仅话题作者可删除图片'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            image = TopicImage.objects.get(id=image_id, topic=topic)
        except TopicImage.DoesNotExist:
            return Response(
                {'error': '图片不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TopicImage.delete() 会同步删除 OSS 文件
        image.delete()

        # 如果没有图片了，更新 has_image
        remaining = TopicImage.objects.filter(topic=topic).count()
        if remaining == 0 and topic.has_image:
            topic.has_image = False
            topic.save(update_fields=['has_image'])

        return Response({'message': '图片已删除'}, status=status.HTTP_200_OK)
    
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
        同时递增话题的 views_count（总浏览量）
        """
        topic = self.get_object()
        record, created = TopicReadRecord.objects.get_or_create(
            topic=topic, user=request.user,
            defaults={'read_count': 1}
        )
        if not created:
            record.read_count += 1
            record.save(update_fields=['read_count'])
        # 原子递增话题浏览量
        Topic.objects.filter(pk=topic.pk).update(views_count=F('views_count') + 1)
        topic.refresh_from_db(fields=['views_count'])
        return Response({
            'is_read': True,
            'read_count': record.read_count,
            'views_count': topic.views_count,
        })
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """获取评论列表 / 添加评论"""
        topic = self.get_object()
        if request.method == 'GET':
            # 顶级评论（含回复预取）
            replies_qs = Comment.objects.filter(
                is_active=True
            ).select_related(
                'author', 'author__neighbor_hub_profile',
                'reply_to', 'reply_to__neighbor_hub_profile',
            ).order_by('created_at')
            comments = Comment.objects.filter(
                topic=topic, parent__isnull=True, is_active=True
            ).select_related(
                'author', 'author__neighbor_hub_profile'
            ).prefetch_related(
                Prefetch('replies', queryset=replies_qs)
            ).order_by('-created_at')
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        # POST 添加评论
        # 已关闭/已隐藏的话题不可评论
        if topic.status != Topic.Status.ACTIVE:
            return Response(
                {'error': '该话题已关闭或已隐藏，不可评论'},
                status=status.HTTP_400_BAD_REQUEST
            )
        content = request.data.get('content', '').strip()
        if not content:
            raise ValidationError({'content': '评论内容不能为空'})
        parent_id = request.data.get('parent')
        parent = None
        reply_to = None
        if parent_id:
            try:
                replied_comment = Comment.objects.get(id=parent_id, topic=topic)
            except Comment.DoesNotExist:
                raise ValidationError({'parent': '父评论不存在'})
            # 扁平化回复模型：
            # - parent 始终指向根评论（顶级评论）
            # - reply_to 指向被回复的用户
            if replied_comment.parent is None:
                # 回复的是顶级评论 → parent 就是它，reply_to 是它的作者
                parent = replied_comment
                reply_to = replied_comment.author
            else:
                # 回复的是某条回复 → parent 提升为根评论，reply_to 是被回复回复的作者
                parent = replied_comment.parent
                reply_to = replied_comment.author
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        comment = Comment.objects.create(
            topic=topic,
            author=request.user,
            author_building=profile.building if profile else '',
            author_role=profile.role if profile else 'owner',
            parent=parent,
            reply_to=reply_to,
            content=content
        )
        topic.comments_count += 1
        topic.save(update_fields=['comments_count'])
        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """置顶/取消置顶话题"""
        topic = self.get_object()
        topic.is_pinned = not topic.is_pinned
        topic.save(update_fields=['is_pinned'])
        return Response({'is_pinned': topic.is_pinned})
    
    @action(detail=True, methods=['post'])
    def hide(self, request, pk=None):
        """隐藏/取消隐藏话题
        
        隐藏后话题不再出现在信息流列表中。
        """
        topic = self.get_object()
        if topic.status == Topic.Status.HIDDEN:
            topic.status = Topic.Status.ACTIVE
        else:
            topic.status = Topic.Status.HIDDEN
        topic.save(update_fields=['status'])
        return Response({'status': topic.status})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """关闭/重新开启话题
        
        关闭后任何人不可编辑、删除、评论。
        """
        topic = self.get_object()
        if topic.status == Topic.Status.CLOSED:
            topic.status = Topic.Status.ACTIVE
        else:
            topic.status = Topic.Status.CLOSED
        topic.save(update_fields=['status'])
        return Response({'status': topic.status})


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
        ).select_related(
            'inviter_community',
            'inviter', 'inviter__neighbor_hub_profile',
            'invitee', 'invitee__neighbor_hub_profile',
        )
    
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
        
        # 重新查询以预取关联数据，避免序列化时 N+1
        invitation = Invitation.objects.select_related(
            'inviter', 'inviter__neighbor_hub_profile',
            'invitee', 'invitee__neighbor_hub_profile',
            'inviter_community',
        ).get(id=invitation.id)
        
        response_serializer = InvitationSerializer(invitation, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

