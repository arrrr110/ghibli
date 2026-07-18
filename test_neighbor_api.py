#!/usr/bin/env python
"""neighbor_hub API test script"""
# -*- coding: utf-8 -*-

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import requests
from users.models import User
from rest_framework_simplejwt.tokens import RefreshToken


def get_test_user():
    user = User.objects.filter(is_staff=False).first()
    if not user:
        user = User.objects.create_user(
            username='test_user', password='test123456',
            phone='13800138000', nickname='Test User'
        )
        from neighbor_hub.models import NeighborHubProfile, Community
        community, _ = Community.objects.get_or_create(
            name='Test Community', defaults={'address': 'Test Address'}
        )
        NeighborHubProfile.objects.get_or_create(
            user=user,
            defaults={'community': community, 'role': 'owner', 'building': '1', 'is_verified': True}
        )
    return user


def test_authenticated():
    user = get_test_user()
    refresh = RefreshToken.for_user(user)
    token = str(refresh.access_token)

    print("=== Test: Authenticated Request ===")
    print(f"User: {user.username}")
    print(f"Phone: {user.phone}")

    url = "http://localhost:8000/api/neighbor-hub/users/me/"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_unauthorized():
    print("\n=== Test: Unauthorized Request ===")
    url = "http://localhost:8000/api/neighbor-hub/users/me/"
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code in (401, 403)


if __name__ == '__main__':
    print("Starting API tests...\n")
    test_unauthorized()
    success = test_authenticated()
    print("\n" + "=" * 40)
    print("SUCCESS" if success else "FAILED")
    print("=" * 40)
