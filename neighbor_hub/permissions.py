from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsVerifiedUser(BasePermission):
    """只允许已认证用户访问"""
    
    message = '您需要完成身份认证后才能执行此操作'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile or not profile.is_verified:
            return False
        return True


class IsCommitteeMember(BasePermission):
    """只允许业委会成员访问"""
    
    message = '只有业委会成员可以执行此操作'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile or profile.role != 'committee':
            return False
        return True


class IsPropertyOrCommittee(BasePermission):
    """允许业委会或物业访问"""
    
    message = '只有业委会或物业可以执行此操作'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if not profile or profile.role not in ('committee', 'property'):
            return False
        return True


class IsAuthorOrReadOnly(BasePermission):
    """只允许作者修改"""
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user


class IsCommitteeOrAuthor(BasePermission):
    """允许业委会或作者操作"""
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.author == request.user:
            return True
        profile = getattr(request.user, 'neighbor_hub_profile', None)
        if profile and profile.role == 'committee':
            return True
        return False
