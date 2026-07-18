from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CurrentUserProfileView,
    CommunityViewSet,
    TopicViewSet,
    InvitationViewSet,
    VerificationRequestViewSet,
    NotificationViewSet,
)

app_name = 'neighbor_hub'

router = DefaultRouter()
router.register(r'communities', CommunityViewSet, basename='community')
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'invitations', InvitationViewSet, basename='invitation')
router.register(r'verification-requests', VerificationRequestViewSet, basename='verification-request')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # 当前用户 Profile
    path('users/me/', CurrentUserProfileView.as_view(), name='current-user-profile'),
    
    # ViewSet 路由
    path('', include(router.urls)),
]
