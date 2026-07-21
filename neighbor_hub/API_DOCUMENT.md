# NeighborHub API 接口文档

> **Base URL**: `http://your-domain.com/api/neighbor-hub/`  
> **认证方式**: JWT (Bearer Token)  
> **数据格式**: JSON  
> **最后更新时间**: 2026-07-19

---

## 认证说明

所有接口（除登录注册外）均需携带 JWT Token：

```
Authorization: Bearer <access_token>
```

如需获取/刷新 Token，请参阅用户认证文档：`/api/users/` 相关接口。

---

## 权限与角色说明

本应用采用 **基于角色的权限控制 (RBAC)**，用户角色通过 `NeighborHubProfile.role` 字段管理。

### 角色定义

| 角色值 | 名称 | 说明 |
|--------|------|------|
| `owner` | 业主 | 已通过身份认证的普通用户 |
| `committee` | 业委会 | 小区业委会成员，拥有管理权限 |
| `property` | 物业 | 物业管理人员 |
| `unverified` | 待认证 | 未认证用户（默认值） |

### 自定义权限类

| 权限类 | 说明 | 适用范围 |
|--------|------|----------|
| `IsAuthenticated` | 已登录用户 | 所有接口 |
| `IsVerifiedUser` | 已完成身份认证的业主/业委会/物业 | 创建话题、点赞、订阅等 |
| `IsCommitteeMember` | 业委会成员 | 小区管理、话题置顶等 |
| `IsCommitteeOrAuthor` | 业委会成员或作者本人 | 话题更新、删除 |
| `IsPropertyOrCommittee` | 物业或业委会成员 | 高级管理操作（预留） |
| `IsAuthorOrReadOnly` | 作者本人可修改，其他只读 | 通用对象级权限（预留） |

---

## 接口路由总览

| 模块 | 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|------|
| 用户档案 | GET | `/users/me/` | 已登录 | 获取当前用户 Profile |
| 用户档案 | PATCH | `/users/me/` | 已登录 | 更新当前用户 Profile（仅 building/bio） |
| 用户档案 | POST | `/users/me/switch-community/` | 已登录 | 切换小区（重置认证状态） |
| 用户档案 | GET | `/users/profile/{user_id}/` | 已登录 | 查询指定用户档案（用于邀请） |
| 小区 | GET | `/communities/` | 已登录 | 小区列表 |
| 小区 | POST | `/communities/` | 已登录 + 业委会 | 创建小区 |
| 小区 | GET | `/communities/{id}/` | 已登录 | 小区详情 |
| 小区 | PATCH | `/communities/{id}/` | 已登录 + 业委会 | 更新小区 |
| 小区 | DELETE | `/communities/{id}/` | 已登录 + 业委会 | 删除小区 |
| 小区 | GET | `/communities/{id}/members/` | 已登录 + 业委会 | 小区成员列表（支持筛选） |
| 小区 | DELETE | `/communities/{id}/members/{user_id}/` | 已登录 + 业委会 | 删除小区成员 |
| 话题 | GET | `/topics/` | 已登录 | 话题列表（支持筛选） |
| 话题 | POST | `/topics/` | 已登录 + 已认证 | 创建话题 |
| 话题 | GET | `/topics/{id}/` | 已登录 | 话题详情 |
| 话题 | PATCH | `/topics/{id}/` | 业委会或作者 | 更新话题 |
| 话题 | DELETE | `/topics/{id}/` | 业委会或作者 | 删除话题 |
| 话题 | POST | `/topics/{id}/like/` | 已登录 + 已认证 | 点赞/取消点赞 |
| 话题 | POST | `/topics/{id}/subscribe/` | 已登录 + 已认证 | 订阅/取消订阅 |
| 话题 | GET | `/topics/{id}/comments/` | 已登录 | 获取评论列表 |
| 话题 | POST | `/topics/{id}/comments/` | 已登录 + 已认证 | 添加评论 |
| 话题 | POST | `/topics/{id}/pin/` | 已登录 + 业委会 | 置顶/取消置顶 |
| 邀请 | GET | `/invitations/` | 已登录 | 我的邀请记录 |
| 邀请 | POST | `/invitations/` | 已登录 | 记录邀请关系（传入 inviter user_id） |
| 邀请 | DELETE | `/invitations/{id}/` | 已登录 | 删除邀请记录 |
| 认证申请 | POST | `/verification-requests/` | 已登录 | 提交认证申请 |
| 认证申请 | GET | `/verification-requests/` | 已登录 | 我的认证申请列表 |
| 认证申请 | GET | `/verification-requests/{id}/` | 已登录 | 认证申请详情 |
| 认证申请 | GET | `/verification-requests/pending/` | 已登录 + 业委会 | 待审核列表 |
| 认证申请 | POST | `/verification-requests/{id}/review/` | 已登录 + 业委会 | 审核认证申请 |
| 通知 | GET | `/notifications/` | 已登录 | 通知列表 |
| 通知 | GET | `/notifications/{id}/` | 已登录 | 通知详情 |
| 通知 | DELETE | `/notifications/{id}/` | 已登录 | 删除通知 |
| 通知 | GET | `/notifications/unread-count/` | 已登录 | 未读通知数量 |
| 通知 | POST | `/notifications/{id}/read/` | 已登录 | 标记单条已读 |
| 通知 | POST | `/notifications/read-all/` | 已登录 | 全部标记已读 |

---

## 一、用户档案接口

---

### 1. 获取当前用户 Profile

**GET** `/users/me/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "nickname": "用户昵称",
  "avatar": "头像URL",
  "phone": "138****8000",
  "community": "uuid-or-null",
  "community_name": "小区名称",
  "role": "owner|committee|property|unverified",
  "building": "1号楼",
  "bio": "个人简介",
  "is_verified": true,
  "verified_at": "2026-07-19T10:00:00Z",
  "verification_note": "审核备注",
  "invited_by": "uuid-or-null",
  "is_active": true,
  "last_login_at": "2026-07-19T10:00:00Z",
  "created_at": "2026-07-19T10:00:00Z",
  "updated_at": "2026-07-19T10:00:00Z"
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | Profile ID |
| user_id | UUID | 用户 ID |
| nickname | string | 用户昵称（neighbor_hub 专属） |
| avatar | string | 头像URL（neighbor_hub 专属） |
| phone | string | 脱敏手机号 |
| community | UUID/null | 所属小区 ID |
| community_name | string | 小区名称 |
| role | string | 用户角色 |
| building | string | 楼号 |
| bio | string | 个人简介 |
| is_verified | boolean | 是否已认证 |
| verified_at | datetime/null | 认证时间 |
| invited_by | UUID/null | 邀请人 ID |
| is_active | boolean | 是否活跃 |

---

### 2. 更新当前用户 Profile

**PATCH** `/users/me/`

**权限**: `IsAuthenticated`

**请求体**:
```json
{
  "nickname": "新昵称",
  "avatar": "https://example.com/avatar.jpg",
  "building": "2号楼",
  "bio": "我是小区热心业主"
}
```

**可修改字段**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| nickname | string | 否 | 昵称（最大50字符） |
| avatar | string | 否 | 头像URL |
| building | string | 否 | 楼号（最大50字符） |
| bio | string | 否 | 个人简介（最大200字符） |

**🔒 系统保护字段**（不可通过此接口修改）：
- `role` - 角色管理需通过认证申请或管理后台
- `is_verified` - 认证状态需通过专门的认证流程
- `community` - 小区切换需使用专用接口 `/users/me/switch-community/`
- `invited_by` - 邀请关系通过邀请流程自动设置
- `verified_by`, `verified_at`, `verification_note` - 认证相关信息由系统管理

**响应 (HTTP 200)**: 更新后的 Profile 对象

---

### 3. 切换小区

**POST** `/users/me/switch-community/`

**权限**: `IsAuthenticated`

**功能说明**:
- 用户可自由切换到任意已激活的小区
- 切换后认证状态自动重置为未认证（`is_verified=False, role=unverified`）
- 用户切换回原小区后，同样需要重新认证
- 小区切换后，用户仅能访问新小区的话题、评论等数据

**请求体**:
```json
{
  "community": "目标小区UUID"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| community | UUID | ✅ | 目标小区 ID（必须存在且已激活） |

**响应 (HTTP 200)**:
```json
{
  "message": "小区切换成功",
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "nickname": "用户昵称",
    "phone": "138****8000",
    "community": "新小区UUID",
    "community_name": "新小区名称",
    "role": "unverified",
    "building": "",
    "is_verified": false,
    "verified_at": null,
    ...
  },
  "meta": {
    "old_community_name": "原小区名称",
    "was_verified": true,
    "old_role": "owner",
    "new_community_name": "新小区名称",
    "requires_reverification": true
  }
}
```

**meta 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| old_community_name | string/null | 切换前的小区名称 |
| was_verified | boolean | 切换前是否已认证 |
| old_role | string | 切换前角色 |
| new_community_name | string | 目标小区名称 |
| requires_reverification | boolean | 是否需要重新认证（始终为 true） |

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 切换到当前小区 | `{"error": "您已经是该小区的成员"}` |
| 404 | 用户档案不存在 | `{"error": "用户档案不存在"}` |
| 400 | 小区参数校验失败 | `{"community": ["目标小区不存在"]}` |
| 400 | 小区未激活 | `{"community": ["目标小区未激活，无法加入"]}` |

---

## 小区切换规则

### 规则说明

当用户切换小区时（通过更新 Profile 的 `community` 字段或重新加入新小区），系统执行以下逻辑：

| 原状态 | 切换后状态 | 说明 |
|--------|-----------|------|
| `is_verified=True, role=owner` | `is_verified=False, role=unverified` | 认证自动失效 |
| `is_verified=True, role=committee` | `is_verified=False, role=unverified` | 业委会身份不继承 |
| `is_verified=False, role=unverified` | 保持不变 | 无影响 |

### 设计理由

1. **认证是小区对用户的认可**——A 小区的业主身份不代表自动获得 B 小区的身份
2. **保障小区安全**——新小区业委会有权审核每位新成员
3. **支持社区自然扩圈**——用户可自由加入新小区，只需重新走认证流程
4. **权益隔离**——旧小区的身份、权限不会自动带入新小区

### 用户引导建议

前端检测到 `is_verified` 由 `true` 变为 `false` 时，建议显示提示：

> 您已切换至新小区，需要重新完成身份认证才能参与小区治理。

### 业委会权限管理

| 规则 | 说明 |
|------|------|
| 创建小区 | 任何已登录用户均可创建小区 |
| 业委会任命 | 仅平台管理员（超级用户）可通过 Django Admin 后台设置用户的 `role=committee` |
| 认证权限 | 只有被任命为业委会的小区才能审核该小区的认证申请 |

> **工作流**：用户创建小区 → 通过邀请或自由加入发展成员 → 管理员在后台任命业委会 → 业委会开始审核成员身份

### 4. 查询用户档案（用于邀请功能）

**GET** `/users/profile/{user_id}/`

**权限**: `IsAuthenticated`

**功能说明**:
- 根据NeighborHubProfile 关联用户ID查询用户档案信息
- 主要用于邀请功能，显示邀请人的用户信息
- 仅返回公开信息，过滤敏感数据
- 不返回被禁用用户的档案（is_active=False）

**URL参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | UUID | ✅ | NeighborHubProfile 的 关联用户ID |

**响应 (HTTP 200)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "nickname": "张三",
  "avatar": "https://example.com/avatar.jpg",
  "role": "owner",
  "role_display": "业主",
  "is_verified": true,
  "community": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "name": "阳光花园"
  },
  "building": "1号楼",
  "bio": "热爱社区生活",
  "member_since": "2024-01-15T10:30:00Z"
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | NeighborHubProfile ID |
| `user_id` | UUID | 关联的用户 ID |
| `nickname` | string | 用户昵称（优先使用档案昵称，否则使用用户名） |
| `avatar` | string/null | 头像URL |
| `role` | string | 用户角色（owner/committee/property） |
| `role_display` | string | 角色显示名称（业主/业委会/物业） |
| `is_verified` | boolean | 是否已认证 |
| `community` | object/null | 所属小区信息 |
| `community.id` | UUID/null | 小区ID |
| `community.name` | string/null | 小区名称 |
| `building` | string | 楼号 |
| `bio` | string | 个人简介 |
| `member_since` | datetime | 加入时间（档案创建时间） |

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 404 | 用户档案不存在或已被禁用 | `{"error": "用户档案不存在或已被禁用"}` |
| 401 | 未认证 | `{"error": "Authentication credentials were not provided."}` |
| 500 | 服务器内部错误 | `{"error": "服务器内部错误"}` |

**使用场景**:

1. **邀请新用户**: 前端通过URL参数获取邀请人profile_id，调用此接口显示邀请人信息
2. **用户信息展示**: 显示其他用户的基本信息（不敏感信息）
3. **社区成员查询**: 查询小区内其他用户的公开档案

**示例**: 邀请流程
```
URL: https://app.example.com/register?inviter_profile=550e8400-e29b-41d4-a716-446655440001

前端获取邀请人信息:
GET /api/neighbor-hub/users/profile/550e8400-e29b-41d4-a716-446655440001/

显示: "张三（阳光花园 业主）邀请您加入业主黑板报"
```

---

## 二、小区接口

---

### 3. 小区列表

**GET** `/communities/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "name": "阳光花园",
    "address": "北京市朝阳区xxx路100号",
    "description": "高品质住宅小区",
    "is_active": true,
    "established_at": "2015-06-01",
    "members_count": 120,
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
]
```

---

### 4. 创建小区

**POST** `/communities/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**请求体**:
```json
{
  "name": "阳光花园",
  "address": "北京市朝阳区xxx路100号",
  "description": "高品质住宅小区",
  "established_at": "2015-06-01"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 小区名称（最大100字符） |
| address | string | ✅ | 小区地址（最大255字符） |
| description | string | 否 | 小区描述 |
| established_at | date | 否 | 建成日期（格式：YYYY-MM-DD） |

**响应 (HTTP 201)**: 创建的小区详情

**说明**: `created_by` 字段自动设置为当前用户。

---

### 5. 小区详情

**GET** `/communities/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**: 小区详情对象

---

### 6. 更新小区

**PATCH** `/communities/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**请求体**:
```json
{
  "name": "阳光花园二期",
  "description": "新描述"
}
```

**响应 (HTTP 200)**: 更新后的小区详情

---

### 7. 删除小区

**DELETE** `/communities/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**响应 (HTTP 204)**: No Content

---

### 8. 小区成员列表

**GET** `/communities/{id}/members/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅业委会可访问）

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_verified | boolean | 否 | 按认证状态筛选：`true` 已认证 / `false` 未认证 |
| role | string | 否 | 按角色筛选：`owner`/`committee`/`property`/`unverified` |

**请求示例**:
```
GET /communities/{id}/members/?is_verified=false&role=unverified
GET /communities/{id}/members/?is_verified=true
GET /communities/{id}/members/?role=owner
```

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "nickname": "张三",
    "phone": "138****1234",
    "community": "uuid",
    "community_name": "阳光花园",
    "role": "owner",
    "building": "1号楼",
    "is_verified": true,
    ...
  }
]
```

**说明**: 
- 仅返回 `is_active=true` 的活跃成员
- 非业委会成员调用返回 403

---

### 9. 删除小区成员

**DELETE** `/communities/{id}/members/{user_id}/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅业委会可操作）

**功能说明**:
删除小区成员（方案A：最小删除）

| 操作 | 内容 |
|------|------|
| 删除 | `UserAppProfile`（移除 neighbor_hub 应用访问权） |
| 软删除 | `NeighborHubProfile`（`is_active=False`，昵称改为"已注销用户"） |
| 保留 | `User` 基础账户、`Topic`/`Comment` 等历史数据、`Invitation` 邀请记录 |

**限制**:
- 不能删除自己
- 不能删除其他业委会成员
- 只能删除本小区成员

**请求示例**:
```
DELETE /communities/550e8400-e29b-41d4-a716-446655440000/members/660e8400-e29b-41d4-a716-446655440001/
```

**响应 (HTTP 200)**:
```json
{
  "message": "成员已从小区移除"
}
```

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 删除自己 | `{"error": "不能删除自己"}` |
| 400 | 用户不属于本小区 | `{"error": "该用户不属于本小区"}` |
| 403 | 无权限 | `{"error": "仅业委会成员可删除成员"}` |
| 403 | 删除其他业委会 | `{"error": "不能删除其他业委会成员"}` |
| 404 | 用户不存在 | `{"error": "用户不存在"}` |
| 404 | 非活跃成员 | `{"error": "该用户不是小区活跃成员"}` |

---

## 三、话题接口

---

### 10. 话题列表

**GET** `/topics/`

**权限**: `IsAuthenticated`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| community | UUID | 否 | 按小区筛选 |
| category | string | 否 | 按分类筛选 |
| status | string | 否 | 按状态筛选，默认 `active` |
| search | string | 否 | 搜索标题/内容（模糊匹配） |

**category 可选值**:

| 值 | 名称 |
|----|------|
| `facility` | 设施改造 |
| `notice` | 物业通知 |
| `neighbor` | 邻里关系 |
| `environment` | 环境治理 |
| `repair` | 设施维修 |
| `help` | 邻里互助 |
| `announcement` | 业委会公告 |
| `activity` | 社区活动 |
| `dispute` | 邻里纠纷 |
| `other` | 其他 |

**请求示例**: `/topics/?community=uuid&category=notice&search=电梯`

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "community": "uuid",
    "community_name": "阳光花园",
    "author": "uuid",
    "author_nickname": "张三",
    "author_building": "1号楼",
    "author_role": "owner",
    "title": "关于电梯维修的通知",
    "category": "notice",
    "has_image": false,
    "image_url": "",
    "poster_style": "minimal",
    "likes_count": 5,
    "comments_count": 3,
    "views_count": 50,
    "status": "active",
    "is_pinned": false,
    "is_liked": true,
    "is_subscribed": false,
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
]
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| is_liked | boolean | 当前用户是否已点赞 |
| is_subscribed | boolean | 当前用户是否已订阅 |
| has_image | boolean | 是否有配图 |
| poster_style | string | 海报样式：gradient/emoji/minimal |

---

### 10. 创建话题

**POST** `/topics/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`（需已认证）

**请求体**:
```json
{
  "community": "uuid",
  "title": "关于小区绿化的建议",
  "content": "建议在小区增加一些绿植...",
  "category": "environment",
  "has_image": false,
  "image_url": "",
  "poster_style": "minimal",
  "extra_data": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| community | UUID | ✅ | 所属小区 ID |
| title | string | ✅ | 话题标题（2-100字符） |
| content | string | ✅ | 话题内容 |
| category | string | 否 | 分类，默认 `other` |
| has_image | boolean | 否 | 是否有配图，默认 false |
| image_url | string | 否 | 配图 URL |
| poster_style | string | 否 | 海报样式，默认 `minimal` |
| extra_data | object | 否 | 扩展数据 |

**响应 (HTTP 201)**: 创建的话题详情

**说明**: `author`、`author_building`、`author_role` 自动填充。

---

### 11. 话题详情

**GET** `/topics/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**: 话题详情（包含完整 `content`、`extra_data` 和 `comments` 嵌套）

---

### 12. 更新话题

**PATCH** `/topics/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeOrAuthor` 或 `IsCommitteeMember`

**请求体**:
```json
{
  "title": "更新后的标题",
  "content": "更新后的内容"
}
```

**响应 (HTTP 200)**: 更新后的话题详情

---

### 13. 删除话题

**DELETE** `/topics/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeOrAuthor` 或 `IsCommitteeMember`

**响应 (HTTP 204)**: No Content

---

### 14. 点赞/取消点赞

**POST** `/topics/{id}/like/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**响应 (HTTP 200)**:
```json
{
  "liked": true,
  "likes_count": 6
}
```

**说明**: 再次调用可取消点赞，`liked` 相应变为 `false`。

---

### 15. 订阅/取消订阅

**POST** `/topics/{id}/subscribe/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**响应 (HTTP 200)**:
```json
{
  "subscribed": true
}
```

**说明**: 再次调用可取消订阅。

---

### 16. 获取评论列表

**GET** `/topics/{id}/comments/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "topic": "uuid",
    "author": "uuid",
    "author_nickname": "李四",
    "author_avatar": "头像URL",
    "author_building": "2号楼",
    "author_role": "owner",
    "parent": null,
    "content": "支持这个建议！",
    "likes_count": 2,
    "is_active": true,
    "replies_count": 1,
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
]
```

**说明**: 返回顶级评论（parent 为 null），不包含回复（回复需通过 replies 嵌套查看）。

---

### 17. 添加评论

**POST** `/topics/{id}/comments/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**请求体**:
```json
{
  "content": "我也觉得应该这样",
  "parent": "uuid-or-null"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | ✅ | 评论内容（最大1000字符） |
| parent | UUID/null | 否 | 父评论 ID（回复时填写） |

**响应 (HTTP 201)**: 创建的评论详情

**说明**:
- 如果回复的是他人评论，自动发送通知给被回复者
- `author_building` 和 `author_role` 自动从 Profile 填充

---

### 18. 置顶/取消置顶话题

**POST** `/topics/{id}/pin/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**响应 (HTTP 200)**:
```json
{
  "is_pinned": true
}
```

**说明**: 再次调用可取消置顶。

---

## 四、邀请接口

> **H5 场景说明**：
> - **邀请链接格式**: `/join?inviter={user_id}`，**前端自行生成，后端不参与**
> - **邀请流程**:
>   1. 用户A（业主）分享链接给好友
>   2. 好友点击链接打开 H5 注册/登录
>   3. 前端检测到 URL 参数 `inviter`，注册成功后调用 `POST /invitations/` 记录邀请关系

---

### 19. 我的邀请记录

**GET** `/invitations/`

**权限**: `IsAuthenticated`

**说明**: 返回当前用户作为邀请人或被邀请人的所有邀请记录

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "inviter": "uuid",
    "inviter_nickname": "张三",
    "inviter_community": "uuid",
    "community_name": "阳光花园",
    "invitee": "uuid",
    "status": "accepted",
    "expires_at": "2026-08-18T10:00:00Z",
    "accepted_at": "2026-07-19T10:05:00Z",
    "created_at": "2026-07-19T10:05:00Z"
  }
]
```

---

### 20. 记录邀请关系

**POST** `/invitations/`

**权限**: `IsAuthenticated`

**功能说明**:
- 被邀请用户注册/登录成功后，前端检测到 URL 参数 `inviter`，调用此接口记录邀请关系
- `invitee`（被邀请人）自动设为当前登录用户
- 邀请状态直接设为 `accepted`

**请求体**:
```json
{
  "inviter": "邀请人 user_id"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| inviter | UUID | ✅ | 邀请人的 user_id（从 URL 参数获取） |

**响应 (HTTP 201)**:
```json
{
  "id": "uuid",
  "inviter": "uuid",
  "inviter_nickname": "张三",
  "inviter_community": "uuid",
  "community_name": "阳光花园",
  "invitee": "uuid",
  "status": "accepted",
  "expires_at": "2026-08-18T10:00:00Z",
  "accepted_at": "2026-07-19T10:05:00Z",
  "created_at": "2026-07-19T10:05:00Z"
}
```

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 邀请人不存在 | `{"inviter": ["邀请人不存在"]}` |
| 400 | 不能邀请自己 | `{"error": "不能邀请自己"}` |

---

### 21. 删除邀请记录

**DELETE** `/invitations/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 204)**: No Content

---

## 五、身份认证接口

---

### 23. 提交认证申请

**POST** `/verification-requests/`

**权限**: `IsAuthenticated`

**请求体**:
```json
{
  "community": "uuid",
  "name": "张三",
  "phone": "13800138000",
  "building": "1号楼501"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| community | UUID | ✅ | 申请认证的小区 |
| name | string | ✅ | 真实姓名 |
| phone | string | ✅ | 联系电话 |
| building | string | ✅ | 楼号房号 |

**响应 (HTTP 201)**:
```json
{
  "id": "uuid",
  "user": "uuid",
  "user_nickname": "用户昵称",
  "community": "uuid",
  "community_name": "阳光花园",
  "name": "张三",
  "phone": "13800138000",
  "building": "1号楼501",
  "status": "pending",
  "reviewed_by": null,
  "reviewed_by_nickname": null,
  "reviewed_at": null,
  "review_note": "",
  "created_at": "2026-07-19T10:00:00Z",
  "updated_at": "2026-07-19T10:00:00Z"
}
```

**status 可选值**:

| 值 | 名称 |
|----|------|
| `pending` | 待审核 |
| `approved` | 已通过 |
| `rejected` | 已拒绝 |

---

### 24. 我的认证申请列表

**GET** `/verification-requests/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**: 认证申请对象数组

---

### 25. 认证申请详情

**GET** `/verification-requests/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**: 认证申请详情

---

### 26. 待审核列表（业委会）

**GET** `/verification-requests/pending/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**响应 (HTTP 200)**: 当前用户所在小区的待审核申请列表

**说明**: 非业委会成员返回空列表。

---

### 27. 审核认证申请

**POST** `/verification-requests/{id}/review/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**请求体**:
```json
{
  "action": "approve",
  "note": "审核通过，确认为业主"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | ✅ | `approve`（通过）或 `reject`（拒绝） |
| note | string | 否 | 审核备注（最大255字符） |

**响应 (HTTP 200)**:
```json
{
  "status": "approved"
}
```

**说明**:
- 通过后：用户 Profile 的 `is_verified` 设为 `true`，`role` 设为 `owner`，发送通过通知
- 拒绝后：记录拒绝原因，发送拒绝通知

---

## 六、通知接口

---

### 28. 通知列表

**GET** `/notifications/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "type": "verification",
    "title": "身份认证已通过",
    "content": "恭喜！您已成为业主",
    "related_id": "uuid",
    "is_read": false,
    "read_at": null,
    "created_at": "2026-07-19T10:00:00Z"
  }
]
```

**type 可选值**:

| 值 | 名称 |
|----|------|
| `system` | 系统通知 |
| `topic_reply` | 话题回复 |
| `topic_like` | 话题点赞 |
| `verification` | 认证通知 |
| `invitation` | 邀请通知 |

---

### 29. 通知详情

**GET** `/notifications/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**: 通知详情对象

---

### 30. 删除通知

**DELETE** `/notifications/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 204)**: No Content

---

### 31. 未读通知数量

**GET** `/notifications/unread-count/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
{
  "unread_count": 5
}
```

---

### 32. 标记单条通知已读

**POST** `/notifications/{id}/read/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
{
  "read": true
}
```

---

### 33. 全部标记已读

**POST** `/notifications/read-all/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
{
  "message": "已全部标记为已读"
}
```

---

## 统一响应格式

### 成功响应

- GET/GET LIST: `HTTP 200`
- POST (创建成功): `HTTP 201`
- PATCH (更新成功): `HTTP 200`
- DELETE (删除成功): `HTTP 204`
- POST (操作成功): `HTTP 200`

### 错误响应

**字段级错误**:
```json
{
  "field_name": ["错误信息1", "错误信息2"]
}
```

**通用错误**:
```json
{
  "error": "错误描述信息"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无返回体） |
| 400 | 请求参数错误 |
| 401 | 未认证（Token 无效或缺失） |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 前端对接示例

### 典型业务流程

**普通用户流程:**
```
1. 用户登录 → 获得 JWT Token
2. GET /api/neighbor-hub/users/me/ → 获取当前用户 Profile
3. 检查 is_verified 字段:
   - false: 引导用户提交认证申请
   - true: 可正常使用所有功能
4. GET /api/neighbor-hub/topics/ → 浏览话题列表
5. POST /api/neighbor-hub/topics/ → 创建话题（需已认证）
6. 参与互动: 点赞、评论、订阅
```

**邀请注册流程（H5）:**
```
1. 用户A（业主）分享链接: https://域名.com/join?inviter={user_a_id}
2. 好友B 点击链接打开 H5
3. 好友B 注册/登录
4. 前端检测到 URL 参数 inviter=xxx
5. 前端调用 POST /api/neighbor-hub/invitations/ {"inviter": "xxx"}
6. 后端记录邀请关系（invitee=当前用户，status=accepted）
7. 好友B 提交认证申请，业委会审核
```

### Axios 示例

```javascript
// 注意：邀请链接由前端生成，后端不参与
// 格式: https://your-domain.com/join?inviter={user_id}

// 获取小区列表
const getCommunities = async () => {
  const { data } = await axios.get('/api/neighbor-hub/communities/')
  return data
}

// 记录邀请关系 - 被邀请用户登录成功后调用
const recordInvitation = async (inviterId) => {
  // inviterId 从 URL 参数获取: ?inviter=xxx
  const { data } = await axios.post('/api/neighbor-hub/invitations/', {
    inviter: inviterId
  })
  return data
}

// 我的邀请记录
const getMyInvitations = async () => {
  const { data } = await axios.get('/api/neighbor-hub/invitations/')
  return data
}

// 创建话题
const createTopic = async (topicData) => {
  const { data } = await axios.post('/api/neighbor-hub/topics/', topicData)
  return data
}

// 点赞话题
const likeTopic = async (topicId) => {
  const { data } = await axios.post(`/api/neighbor-hub/topics/${topicId}/like/`)
  return data // { liked: true/false, likes_count: 6 }
}

// 提交认证申请
const submitVerification = async (formData) => {
  const { data } = await axios.post('/api/neighbor-hub/verification-requests/', formData)
  return data
}
```

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.4.0 | 2026-07-20 | 用户模型重构：User 只负责基础认证（phone/email/username+password）；nickname、avatar 移至 NeighborHubProfile（应用专属）；UserAppProfile 作为应用标记，业委会可删除应用标记禁用用户访问 |
| v1.3.0 | 2026-07-20 | 邀请系统重构：移除邀请码机制，改为链接+二维码模式；前端生成邀请链接 `/join?inviter={user_id}`；后端只负责记录邀请关系 `POST /invitations/ {"inviter": "xxx"}`；过期时间调整为30天 |
| v1.2.0 | 2026-07-19 | 新增 POST `/users/me/switch-community/` 小区切换接口；新增业委会权限管理规则 |
| v1.1.0 | 2026-07-19 | 新增小区切换规则：切换小区后认证自动失效，需重新认证 |
| v1.0.0 | 2026-07-19 | 初始版本，包含完整的社区治理功能模块 |
