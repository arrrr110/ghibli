"""
neighbor_hub 应用的信号处理器

监听 users 应用的 user_registered 信号，自动创建 NeighborHubProfile
实现 neighbor_hub 与 users 的解耦：
- users 应用发送信号，不关心谁在监听、返回什么
- neighbor_hub 监听信号，自行管理自己的档案数据，自行决定返回什么给前端
"""
import logging
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from users.signals import user_registered
from users.models import User
from .models import NeighborHubProfile, Invitation

logger = logging.getLogger(__name__)


@receiver(user_registered)
def on_user_registered(sender, user, app_name, **kwargs):
    """
    用户注册成功时，自动创建 NeighborHubProfile

    仅当 app_name == 'neighbor_hub' 时才处理
    返回 {'app_name': ..., 'profile_data': {...}} 供 users 透传给前端
    """
    print(f"\n---------- [neighbor_hub] on_user_registered 接收到信号 ----------")
    # print(f"  sender={sender.__name__}")
    # print(f"  user={user.id} ({user.username})")
    # print(f"  app_name={app_name}")
    # print(f"  kwargs={kwargs}")

    if app_name != 'neighbor_hub':
        # print(f"  app_name={app_name} 不是 neighbor_hub，跳过")
        print(f"---------- [neighbor_hub] 信号处理完毕（跳过） ----------")
        return None

    # 基础创建参数（默认业主身份）
    # nickname 由 neighbor_hub 自己决定默认值：
    #   1. 前端传了就用前端的
    #   2. 没传但有手机号，用手机号生成脱敏昵称
    #   3. 没传但有邮箱，用邮箱 @ 前部分
    #   4. 都没有，用用户名
    nickname = kwargs.get('nickname', '')
    if not nickname:
        if user.phone:
            nickname = f'{user.phone[:3]}****{user.phone[-4:]}'
        elif user.email:
            nickname = user.email.split('@')[0]
        else:
            nickname = user.username or str(user.id)[:8]

    defaults = {
        'nickname': nickname,
        'role': NeighborHubProfile.Role.OWNER,
    }

    # 邀请人处理：复制邀请人的小区信息，并创建邀请记录
    invited_by_id = kwargs.get('invited_by')
    if invited_by_id:
        try:
            inviter = User.objects.select_related('neighbor_hub_profile').get(id=invited_by_id)
            inviter_profile = getattr(inviter, 'neighbor_hub_profile', None)

            if inviter_profile and inviter_profile.community_id:
                defaults['community'] = inviter_profile.community
                defaults['invited_by'] = inviter
                logger.info(
                    f'被邀请用户 {user.id} → 小区 {inviter_profile.community_id}, '
                    f'邀请人 {invited_by_id}'
                )

                # 注册即接受邀请，自动创建已接受的邀请记录
                Invitation.objects.get_or_create(
                    inviter=inviter,
                    invitee=user,
                    defaults={
                        'inviter_community': inviter_profile.community,
                        'status': Invitation.Status.ACCEPTED,
                        'accepted_at': timezone.now(),
                        'expires_at': timezone.now() + timedelta(days=30),
                    },
                )
                logger.info(f'邀请记录已创建: 邀请人 {invited_by_id} → 被邀请人 {user.id}')
            else:
                logger.warning(f'邀请人 {invited_by_id} 无小区档案，无法复制小区信息')
        except User.DoesNotExist:
            logger.warning(f'邀请人不存在: {invited_by_id}')

    # get_or_create 确保幂等（即使信号被多次触发也不会重复创建）
    profile, created = NeighborHubProfile.objects.get_or_create(
        user=user,
        defaults=defaults,
    )

    # print(f"  NeighborHubProfile 创建完成: id={profile.id}, created={created}, nickname={profile.nickname}")
    logger.info(f'NeighborHubProfile 创建完成: user={user.id}, created={created}')

    # 返回通用格式：由 neighbor_hub 自己决定返回哪些字段给前端
    # users 只做透传，不关心 profile_data 里有什么
    result = {
        'app_name': 'neighbor_hub',
        'profile_data': {
            'id': str(profile.id),
            'nickname': profile.nickname,
            'is_new_profile': created,
            'is_profile_complete': bool(profile.community),
            'needs_completion': not bool(profile.community),
        }
    }
    # print(f"  返回数据: {result}")
    print(f"---------- [neighbor_hub] 信号处理完毕 ----------")
    return result
