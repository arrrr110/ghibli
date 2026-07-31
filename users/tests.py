from django.test import TestCase
from .models import User, UserAppProfile


class GetAppProfileTest(TestCase):
    """测试 User.get_app_profile() 方法"""

    def setUp(self):
        """准备测试数据"""
        print("\n---------- setUp 开始 ----------")
        self.user = User.objects.create_user(
            username="testuser",
            phone="13800000000",
        )
        print(f"  创建用户: id={self.user.id}, username={self.user.username}, phone={self.user.phone}")

        # 给用户创建两个应用的 Profile
        self.profile_ghibli = UserAppProfile.objects.create(
            user=self.user, app_name="ghibli"
        )
        print(f"  创建 Profile: app_name=ghibli, pk={self.profile_ghibli.pk}")

        self.profile_hub = UserAppProfile.objects.create(
            user=self.user, app_name="neighbor_hub"
        )
        print(f"  创建 Profile: app_name=neighbor_hub, pk={self.profile_hub.pk}")

        print(f"  当前数据库中 User 数量: {User.objects.count()}")
        print(f"  当前数据库中 UserAppProfile 数量: {UserAppProfile.objects.count()}")
        print("---------- setUp 完成 ----------")

    def test_get_existing_profile(self):
        """能正确获取已存在的应用 Profile"""
        print("\n[测试1] test_get_existing_profile: 查询已存在的 ghibli Profile")

        profile = self.user.get_app_profile("ghibli")
        print(f"  查询结果: profile={profile}")
        print(f"  -> app_name={profile.app_name}, pk={profile.pk}")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.app_name, "ghibli")
        self.assertEqual(profile.pk, self.profile_ghibli.pk)
        print("  ✓ 断言通过: Profile 存在且匹配")

    def test_get_nonexistent_profile(self):
        """应用 Profile 不存在时返回 None"""
        print("\n[测试2] test_get_nonexistent_profile: 查询不存在的应用 'non_existent_app'")

        profile = self.user.get_app_profile("non_existent_app")
        print(f"  查询结果: profile={profile}")

        self.assertIsNone(profile)
        print("  ✓ 断言通过: 返回 None，符合预期")

    def test_get_correct_profile_when_multiple(self):
        """用户有多个应用 Profile 时，返回正确的那个"""
        print("\n[测试3] test_get_correct_profile_when_multiple: 用户有多个 Profile，查询 neighbor_hub")

        profile = self.user.get_app_profile("neighbor_hub")
        print(f"  查询结果: profile={profile}")
        print(f"  -> app_name={profile.app_name}, pk={profile.pk}")
        print(f"  对比 ghibli Profile: pk={self.profile_ghibli.pk}")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.app_name, "neighbor_hub")
        self.assertNotEqual(profile.pk, self.profile_ghibli.pk)
        print("  ✓ 断言通过: 返回的是 neighbor_hub 的 Profile，不是 ghibli 的")

    def test_get_profile_is_isolated_per_user(self):
        """不同用户的 Profile 互相隔离"""
        print("\n[测试4] test_get_profile_is_isolated_per_user: 验证不同用户的 Profile 隔离")

        other_user = User.objects.create_user(
            username="otheruser", phone="13900000000", email="other@example.com"
        )
        print(f"  创建第二个用户: id={other_user.id}, username={other_user.username}")
        other_profile = UserAppProfile.objects.create(user=other_user, app_name="ghibli")
        print(f"  为第二个用户创建 Profile: app_name=ghibli, pk={other_profile.pk}")

        print(f"  当前数据库中 User 数量: {User.objects.count()}")
        print(f"  当前数据库中 UserAppProfile 数量: {UserAppProfile.objects.count()}")

        # self.user 只能拿到自己的 profile，不会拿到 other_user 的
        profile = self.user.get_app_profile("ghibli")
        print(f"  用户 {self.user.username} 查询 ghibli Profile -> pk={profile.pk}, user={profile.user.username}")
        print(f"  用户 {other_user.username} 的 ghibli Profile -> pk={other_profile.pk}")

        self.assertEqual(profile.user, self.user)
        self.assertNotEqual(profile.pk, other_profile.pk)
        print("  ✓ 断言通过: 两个用户的 Profile 互相隔离，没有串号")
