from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CurrentUserProfileView,
    UserStatsView,
    UserProfileLookupView,
    SwitchCommunityView,
    AvatarUploadView,
    CommunityViewSet,
    TopicViewSet,
    InvitationViewSet,
)

app_name = 'neighbor_hub'

router = DefaultRouter()
router.register(r'communities', CommunityViewSet, basename='community')
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'invitations', InvitationViewSet, basename='invitation')

urlpatterns = [
    # 切换小区（必须注册在 users/me/ 之前，否则会被 users/me/ 匹配）
    path('users/me/switch-community/', SwitchCommunityView.as_view(), name='user-community'),
    # 用户统计（必须在 users/me/ 之前注册）
    path('users/me/stats/', UserStatsView.as_view(), name='user-stats'),
    # 上传用户头像
    path('users/me/avatar/', AvatarUploadView.as_view(), name='user-avatar-upload'),
    # 当前用户 Profile
    path('users/me/', CurrentUserProfileView.as_view(), name='current-user-profile'),
    # 用户档案查询（用于邀请功能）
    path('users/profile/<uuid:user_id>/', UserProfileLookupView.as_view(), name='user-profile-lookup'),
    
    # ViewSet 路由
    path('', include(router.urls)),
]
