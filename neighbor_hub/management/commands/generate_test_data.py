"""
生成测试数据命令
使用: python manage.py generate_test_data
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from neighbor_hub.models import (
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


User = get_user_model()


# ============ 测试数据池 ============

COMMUNITY_NAMES = [
    ("翡翠湾花园", "上海市浦东新区翡翠路888号"),
    ("阳光新城", "北京市朝阳区阳光大街120号"),
    ("龙湖春江郦城", "杭州市西湖区龙湖路66号"),
    ("万科城市花园", "深圳市南山区万科大道99号"),
    ("保利天悦", "广州市天河区保利路200号"),
    ("绿城桂花城", "南京市建邺区绿城路55号"),
    ("碧桂园凤凰城", "成都市武侯区碧桂园路77号"),
    ("恒大华府", "武汉市洪山区恒大大道100号"),
]

NICKNAMES = [
    "小明", "阿华", "老王", "李阿姨", "陈哥", "张姐", "刘叔", "赵阿姨",
    "周哥", "吴敏", "郑浩", "孙丽", "杨强", "朱琳", "马超", "胡婷",
    "林峰", "何静", "罗辉", "梁芳", "宋杰", "唐敏", "韩磊", "冯丽",
    "董涛", "萧雅", "程刚", "曹颖", "袁斌", "邓超", "傅园", "沈冰",
    "彭丹", "吕刚", "苏菲", "卢伟", "蒋丽", "蔡明", "贾勇", "薛婷",
]

BUILDINGS = [
    "1栋", "2栋", "3栋", "5栋", "6栋", "7栋", "8栋", "9栋", "10栋",
    "11栋", "12栋", "15栋", "16栋", "18栋", "20栋",
]

TOPIC_TEMPLATES = [
    # 设施改造
    ("{building}单元门禁系统老化，建议更换", "facility", 
     "我们楼栋的门禁系统已经用了8年，经常失灵，刷卡没反应。建议物业尽快安排更换，预算约2万元，希望业委会批准。"),
    ("小区儿童游乐设施需要更新", "facility",
     "现有的儿童滑梯和秋千锈迹斑斑，存在安全隐患。我联系了厂家报价，全套更换需要5万元，附件是报价单，请各位委员审阅。"),
    ("地下车库手机信号覆盖问题", "facility",
     "B2层手机完全没有信号，紧急情况无法求救。建议信号运营商来现场勘测，尽快安装信号增强设备。"),
    # 物业通知
    ("关于电梯年检的通知", "notice",
     "根据特种设备管理规定，小区12部电梯需在月底完成年检，可能会有临时停运，请大家提前安排出行。"),
    ("物业费调整征求意见", "notice",
     "因人工成本和材料上涨，物业费拟从2.5元上调至3.0元/平方米，现征求意见，欢迎大家提出看法。"),
    # 邻里关系
    ("楼上噪音扰民问题", "neighbor",
     "楼上住户每晚11点后还有很大噪音，沟通过几次没有效果，希望物业帮忙协调或者业委会出面。"),
    ("楼下商铺油烟扰民", "neighbor",
     "底商开了烧烤店，油烟直排到小区里，味道很大，窗户都不敢开。请相关部门介入处理。"),
    # 环境治理
    ("垃圾分类执行不到位", "environment",
     "虽然有了分类垃圾桶，但很多业主还是混扔，也没有人督导。建议加强宣传和巡查。"),
    ("小区绿化带被占用种菜", "environment",
     "三楼住户在公共绿化带种菜施肥，气味很大影响其他业主，麻烦物业联系整改。"),
    # 设施维修
    ("单元门口路灯不亮", "repair",
     "3栋2单元门口路灯坏了半个月，晚上很黑，老人出行不安全，请尽快维修。"),
    ("楼道感应灯故障汇总", "repair",
     "统计了1-5栋所有楼道的感应灯，共发现15处故障，已拍照存档，请物业统一维修。"),
    # 邻里互助
    ("寻找走失宠物狗泰迪", "help",
     '家中泰迪犬于今早在小区南门走失，名叫"多多"，棕色小型犬，脖子上有蓝色项圈，看到请联系我重谢！'),
    ("求助有经验的电工师傅", "help",
     "家里插座突然没电，没跳闸但没电，有经验的师傅麻烦帮忙看看，有偿感谢。"),
    # 业委会公告
    ("第六届业委会选举结果公示", "announcement",
     "经过业主投票选举，第六届业委会委员名单如下：主任张三、副主任李四...，公示期7天。"),
    ("小区公共收益收支公示（Q1）", "announcement",
     "第一季度公共收益收入12.5万元（车位费等），支出8.2万元（公共设施维护），结余4.3万元。明细见附件。"),
    # 社区活动
    ("端午节包粽子活动报名", "activity",
     "为弘扬传统文化，业委会将于端午节当天举办包粽子活动，名额30人，欢迎报名！"),
    ("暑期少儿篮球培训班", "activity",
     "社区联合体育机构开设暑期篮球班，适合8-14岁少儿，费用全免费，请有需要的业主报名。"),
    # 邻里纠纷
    ("邻居漏水拒不维修", "dispute",
     "楼上卫生间漏水到我家，导致卧室墙面发霉，沟通多次对方拒绝维修，请业委会协调或提供法律援助。"),
    ("车位被占维权", "dispute",
     "我的产权车位被陌生车辆占用三天，车主态度恶劣拒绝挪车，已报警但希望业委会协助解决。"),
    # 其他
    ("建议增设快递柜", "other",
     "目前快递柜只有东门有，西门住的业主取快递很不方便，建议在西门也增设一组。"),
    ("希望增加小区监控探头", "other",
     "3号楼和5号楼之间是监控盲区，已经发生多起电动车电瓶被盗事件，建议加装摄像头。"),
    ("关于小区养犬管理", "other",
     "小区养犬问题越来越严重，遛狗不拴绳、粪便不清理现象普遍，建议制定小区养犬公约。"),
    ("暑期防溺水安全提醒", "other",
     "暑假到了，小区池塘边请家长看好孩子，不要让孩子在水边玩耍，注意安全。"),
    ("闲置物品置换活动倡议", "other",
     "建议每季度组织一次闲置物品置换活动，既环保又能促进邻里交流，大家觉得如何？"),
    ("热心业主感谢信", "other",
     "感谢6栋王师傅免费帮大家磨刀，还有李阿姨义务清扫楼道，这样的热心人咱们小区越来越多！"),
]

COMMENT_TEMPLATES = [
    "支持！这个问题确实该解决了。",
    "业委会尽快处理吧，拖了很久了。",
    "我家的情况也是这样，希望能一起解决。",
    "费用出处是什么？公共维修基金吗？",
    "已经反映了多次了，请给个时间表。",
    "物业看到了吗？请回复进度。",
    "点赞！这届业委会办事效率高。",
    "我不赞成这个方案，建议重新讨论。",
    "可以先在公告栏贴个通知试试效果。",
    "我周末有空，可以作为志愿者参与。",
    "上次开会说的事怎么又没下文了？",
    "可以的，算我一个，支持社区活动。",
    "应该在业主群里再征集一下意见。",
    "请问现在进展如何了？",
    "好事情，期待更多类似的活动！",
    "这个费用需要业主共同承担吗？",
    "能不能先做一个详细的预算方案？",
    "已经打过电话了，等回复。",
    "同意楼主观点，不能再拖了。",
    "辛苦了，感谢业委会的付出！",
]

NOTIFICATION_TEMPLATES = [
    ("系统通知", "欢迎加入NeighborHub社区，完善个人资料并与邻居互动。", "system"),
    ("认证通过", "您的身份认证已通过，现在可以参与社区讨论啦。", "verification"),
    ("话题回复", "有人回复了您的话题《{title}》，快去看看。", "topic_reply"),
    ("话题点赞", "您的收到了 {count} 个赞。", "topic_like"),
    ("邀请通知", "{inviter} 邀请您加入社区，请尽快注册。", "invitation"),
    ("公告提醒", "社区有新公告《{title}》，请注意查看。", "system"),
]


class Command(BaseCommand):
    help = '生成测试数据（users + neighbor_hub）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=30,
            help='生成用户数量（默认30）'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='清除现有测试数据后重新生成'
        )

    def handle(self, *args, **options):
        user_count = options['users']
        clean = options['clean']

        if clean:
            self.stdout.write(self.style.WARNING('清除现有数据...'))
            self.clean_data()

        self.stdout.write(self.style.SUCCESS(f'开始生成测试数据（{user_count} 个用户）...'))

        # 1. 创建小区
        communities = self.create_communities()
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(communities)} 个小区'))

        # 2. 创建用户 + UserAppProfile
        users = self.create_users_and_profiles(user_count)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(users)} 个用户'))

        # 3. 创建 NeighborHubProfile
        profiles = self.create_neighbor_profiles(users, communities)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(profiles)} 个用户档案'))

        # 4. 创建邀请记录
        invitations = self.create_invitations(users, communities)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(invitations)} 条邀请记录'))

        # 5. 创建认证申请
        verification_requests = self.create_verification_requests(users, communities)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(verification_requests)} 条认证申请'))

        # 6. 创建话题
        topics = self.create_topics(users, communities)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(topics)} 个话题'))

        # 7. 创建评论
        comments = self.create_comments(users, topics)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(comments)} 条评论'))

        # 8. 创建点赞
        likes_count = self.create_likes(users, topics)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {likes_count} 条点赞'))

        # 9. 创建订阅
        subs_count = self.create_subscriptions(users, topics)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {subs_count} 条订阅'))

        # 10. 创建通知
        notifications = self.create_notifications(users, topics)
        self.stdout.write(self.style.SUCCESS(f'  创建了 {len(notifications)} 条通知'))

        self.stdout.write(self.style.SUCCESS('测试数据生成完成！'))

    def clean_data(self):
        """清除测试数据"""
        from users.models import UserAppProfile, LoginRecord
        
        # 顺序很重要，先清关联数据
        AppNotification.objects.all().delete()
        TopicLike.objects.all().delete()
        TopicSubscription.objects.all().delete()
        Comment.objects.all().delete()
        Topic.objects.all().delete()
        VerificationRequest.objects.all().delete()
        Invitation.objects.all().delete()
        NeighborHubProfile.objects.all().delete()
        Community.objects.all().delete()
        UserAppProfile.objects.filter(app_name='neighbor_hub').delete()
        # 只清除phone用户，不清除可能存在的superuser
        User.objects.exclude(is_superuser=True).delete()

    def create_communities(self):
        """创建小区"""
        communities = []
        for name, address in COMMUNITY_NAMES:
            community, created = Community.objects.get_or_create(
                name=name,
                defaults={
                    'address': address,
                    'description': f'{name}建成于{random.randint(2005, 2020)}年，共有{random.randint(8, 25)}栋住宅楼。',
                    'established_at': f'{random.randint(2005, 2020)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}',
                    'is_active': True,
                }
            )
            if created:
                communities.append(community)
        return Community.objects.all()

    def create_users_and_profiles(self, count):
        """创建用户和 UserAppProfile"""
        users = []
        base_phone = 13800000000
        
        for i in range(count):
            phone = str(base_phone + i)
            username = f'user_{phone[-8:]}'
            
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'username': username,
                }
            )
            
            if created:
                # 生成 UserAppProfile
                from users.models import UserAppProfile
                UserAppProfile.objects.get_or_create(
                    user=user,
                    app_name='neighbor_hub',
                )
                users.append(user)
            else:
                # 确保已有用户也有AppProfile
                from users.models import UserAppProfile
                UserAppProfile.objects.get_or_create(
                    user=user,
                    app_name='neighbor_hub',
                )
                users.append(user)
        
        return users

    def create_neighbor_profiles(self, users, communities):
        """创建 NeighborHubProfile"""
        profiles = []
        
        # 第一个用户设为翡翠湾的业委会
        committee_user = users[0]
        
        for i, user in enumerate(users):
            # 角色分配：第0个是业委会，第1-2是物业，大部分是业主，少量待认证
            if i == 0:
                role = NeighborHubProfile.Role.COMMITTEE
                is_verified = True
            elif i <= 2:
                role = NeighborHubProfile.Role.PROPERTY
                is_verified = True
            elif i <= 28:
                role = NeighborHubProfile.Role.OWNER
                is_verified = random.choice([True, True, True, False])  # 75%通过
            else:
                role = NeighborHubProfile.Role.OWNER
                is_verified = False
            
            # 分配小区
            community = random.choice(list(communities))
            
            # 楼号
            building = random.choice(BUILDINGS)
            
            profile, created = NeighborHubProfile.objects.get_or_create(
                user=user,
                defaults={
                    'nickname': NICKNAMES[i % len(NICKNAMES)],
                    'avatar': f'https://api.dicebear.com/7.x/micah/svg?seed={user.username}',
                    'bio': random.choice([
                        '热爱社区生活', '新搬来的住户', '住了10年的老邻居',
                        '希望小区越来越好', '乐于助人', '',
                        '喜欢植物，阳台养了很多花', '两个孩子的妈妈',
                        '退休在家，有时间参与社区事务', '上班族，工作日较忙',
                    ]),
                    'community': community,
                    'role': role,
                    'building': building,
                    'is_verified': is_verified,
                    'verified_by': committee_user if is_verified else None,
                    'verified_at': timezone.now() - timedelta(days=random.randint(1, 30)) if is_verified else None,
                    'invited_by': random.choice(users[:max(1, i)]) if i > 0 and random.random() < 0.5 else None,
                }
            )
            if created:
                profiles.append(profile)
        
        return profiles

    def create_invitations(self, users, communities):
        """创建邀请记录"""
        invitations = []
        
        for _ in range(30):
            inviter = random.choice(users)
            inviter_profile = NeighborHubProfile.objects.filter(user=inviter).first()
            if not inviter_profile or not inviter_profile.community:
                continue
            
            status = random.choices(
                [Invitation.Status.PENDING, Invitation.Status.ACCEPTED, 
                 Invitation.Status.EXPIRED, Invitation.Status.CANCELLED],
                weights=[20, 60, 10, 10]
            )[0]
            
            invitee = None
            accepted_at = None
            if status == Invitation.Status.ACCEPTED:
                invitee = random.choice([u for u in users if u != inviter])
                accepted_at = timezone.now() - timedelta(days=random.randint(0, 7))
            
            invitation = Invitation.objects.create(
                inviter=inviter,
                inviter_community=inviter_profile.community,
                invitee=invitee,
                status=status,
                expires_at=timezone.now() + timedelta(days=random.choice([-7, 1, 3, 7])),
                accepted_at=accepted_at,
            )
            invitations.append(invitation)
        
        return invitations

    def create_verification_requests(self, users, communities):
        """创建认证申请"""
        requests = []
        committee_users = NeighborHubProfile.objects.filter(
            role=NeighborHubProfile.Role.COMMITTEE
        ).values_list('user', flat=True)
        
        for _ in range(30):
            user = random.choice(users)
            profile = NeighborHubProfile.objects.filter(user=user).first()
            if not profile or not profile.community:
                continue
            
            status = random.choices(
                [VerificationRequest.Status.PENDING,
                 VerificationRequest.Status.APPROVED,
                 VerificationRequest.Status.REJECTED],
                weights=[25, 60, 15]
            )[0]
            
            reviewed_by = None
            reviewed_at = None
            review_note = ''
            if status == VerificationRequest.Status.APPROVED:
                reviewed_by_id = random.choice(list(committee_users)) if committee_users else None
                if reviewed_by_id:
                    reviewed_by = User.objects.get(id=reviewed_by_id)
                reviewed_at = timezone.now() - timedelta(days=random.randint(0, 5))
                review_note = random.choice([
                    '已通过房本核验', '材料齐全，审核通过', '现场核实通过',
                ])
            elif status == VerificationRequest.Status.REJECTED:
                reviewed_by_id = random.choice(list(committee_users)) if committee_users else None
                if reviewed_by_id:
                    reviewed_by = User.objects.get(id=reviewed_by_id)
                reviewed_at = timezone.now() - timedelta(days=random.randint(0, 5))
                review_note = random.choice([
                    '房产证名字不符，请重新提交', '缺少物业缴费凭证',
                    '照片模糊，请上传清晰的证件照',
                ])
            
            req = VerificationRequest.objects.create(
                user=user,
                community=profile.community,
                name=profile.nickname or user.username,
                phone=user.phone or '',
                building=profile.building,
                status=status,
                reviewed_by=reviewed_by,
                reviewed_at=reviewed_at,
                review_note=review_note,
            )
            requests.append(req)
        
        return requests

    def create_topics(self, users, communities):
        """创建话题"""
        topics = []
        committee_users = list(NeighborHubProfile.objects.filter(
            role=NeighborHubProfile.Role.COMMITTEE
        ).values_list('user', flat=True))
        
        for i, (title_template, category, content) in enumerate(TOPIC_TEMPLATES):
            author = random.choice(users)
            profile = NeighborHubProfile.objects.filter(user=author).first()
            if not profile or not profile.community:
                author = users[0]
                profile = NeighborHubProfile.objects.filter(user=author).first()
            
            # 业委会发的公告类话题置顶
            is_pinned = profile.role == NeighborHubProfile.Role.COMMITTEE and category in ['announcement', 'notice']
            
            topic = Topic.objects.create(
                community=profile.community,
                author=author,
                author_building=profile.building,
                author_role=profile.role,
                title=title_template.format(building=profile.building),
                content=content,
                category=category,
                has_image=random.random() < 0.3,
                poster_style=random.choice([
                    Topic.PosterStyle.GRADIENT,
                    Topic.PosterStyle.EMOJI,
                    Topic.PosterStyle.MINIMAL,
                ]),
                likes_count=random.randint(0, 50),
                comments_count=random.randint(0, 30),
                views_count=random.randint(10, 500),
                status=random.choice([
                    Topic.Status.ACTIVE, Topic.Status.ACTIVE, Topic.Status.ACTIVE,
                    Topic.Status.CLOSED, Topic.Status.PENDING,
                ]),
                is_pinned=is_pinned,
            )
            topics.append(topic)
        
        return topics

    def create_comments(self, users, topics):
        """创建评论"""
        comments = []
        
        for topic in topics:
            comment_count = random.randint(3, 12)
            for _ in range(comment_count):
                author = random.choice(users)
                profile = NeighborHubProfile.objects.filter(user=author).first()
                if not profile:
                    continue
                
                parent = None
                # 30% 概率是回复其他评论
                existing_comments = [c for c in comments if c.topic == topic]
                if existing_comments and random.random() < 0.3:
                    parent = random.choice(existing_comments)
                
                comment = Comment.objects.create(
                    topic=topic,
                    author=author,
                    author_building=profile.building,
                    author_role=profile.role,
                    parent=parent,
                    content=random.choice(COMMENT_TEMPLATES),
                    likes_count=random.randint(0, 10),
                )
                comments.append(comment)
            
            # 更新话题评论数
            topic.comments_count = len([c for c in comments if c.topic == topic])
            topic.save(update_fields=['comments_count'])
        
        return comments

    def create_likes(self, users, topics):
        """创建话题点赞"""
        count = 0
        for topic in topics:
            like_users = random.sample(users, min(random.randint(5, 15), len(users)))
            for user in like_users:
                _, created = TopicLike.objects.get_or_create(
                    topic=topic,
                    user=user,
                )
                if created:
                    count += 1
        return count

    def create_subscriptions(self, users, topics):
        """创建话题订阅"""
        count = 0
        for topic in topics:
            sub_users = random.sample(users, min(random.randint(3, 8), len(users)))
            for user in sub_users:
                _, created = TopicSubscription.objects.get_or_create(
                    topic=topic,
                    user=user,
                )
                if created:
                    count += 1
        return count

    def create_notifications(self, users, topics):
        """创建应用内通知"""
        notifications = []
        
        for _ in range(35):
            user = random.choice(users)
            notif_type = random.choice([t[2] for t in NOTIFICATION_TEMPLATES])
            
            title = ''
            content = ''
            
            if notif_type == 'system':
                title = random.choice(['系统通知', '公告提醒', '活动通知'])
                content = '欢迎参与社区建设，共建美好生活。'
            elif notif_type == 'verification':
                title = '认证通过'
                content = '您的身份认证已通过，享受更多社区权益。'
            elif notif_type == 'topic_reply':
                topic = random.choice(topics)
                title = '话题回复'
                content = f'有人回复了您关注的话题《{topic.title}》'
            elif notif_type == 'topic_like':
                title = '收到点赞'
                content = f'您的内容获得了 {random.randint(1, 20)} 个赞'
            elif notif_type == 'invitation':
                title = '社区邀请'
                content = '有邻居邀请您加入社区，快来看看吧'
            
            notif = AppNotification.objects.create(
                user=user,
                type=notif_type,
                title=title,
                content=content,
                related_id=str(random.choice(topics).id) if topics and random.random() < 0.5 else '',
                is_read=random.random() < 0.4,
                read_at=timezone.now() - timedelta(hours=random.randint(1, 24)) if random.random() < 0.4 else None,
            )
            notifications.append(notif)
        
        return notifications
