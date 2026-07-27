# NeighborHub API 接口文档 v2

> **Base URL**: `http://your-domain.com/api/neighbor-hub/`  
> **认证方式**: JWT (Bearer Token)  
> **数据格式**: JSON  
> **最后更新时间**: 2026-07-27  
> **文档版本**: v2.5.0

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

### 自定义权限类

| 权限类 | 说明 | 适用范围 |
|--------|------|----------|
| `IsAuthenticated` | 已登录用户 | 所有接口 |
| `IsVerifiedUser` | 已完成身份认证的业主/业委会/物业 | 创建话题、点赞、订阅等 |
| `IsCommitteeMember` | 业委会成员 | 小区管理、话题置顶等 |
| `IsCommitteeOrAuthor` | 业委会成员或作者本人 | 话题更新、删除 |

> **安全规则**：业委会成员只能管理 **自己所属小区** 的成员和话题。跨小区管理操作会被 `get_queryset()` 过滤拦截，返回 404。

---

## 接口路由总览

| 模块 | 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|------|
| 用户档案 | GET | `/users/me/` | 已登录 | 获取当前用户 Profile（含 `my_communities`） |
| 用户档案 | PATCH | `/users/me/` | 已登录 | 更新当前用户 Profile |
| 用户档案 | GET | `/users/me/stats/` | 已登录 | **新增** 获取当前用户聚合统计 |
| 用户档案 | POST | `/users/me/switch-community/` | 已登录 | 切换/退出小区 |
| 用户档案 | POST | `/users/me/avatar/` | 已登录 | 上传用户头像 |
| 用户档案 | GET | `/users/profile/{user_id}/` | 已登录 | 查询指定用户档案（用于邀请） |
| 小区 | GET | `/communities/` | 已登录 | 小区列表（默认仅已激活；`?mine=1` 查看自己创建的含未激活） |
| 小区 | POST | `/communities/` | 已登录 | 创建小区（非管理员创建的 `is_active=False`，待 admin 审核） |
| 小区 | GET | `/communities/{id}/` | 已登录 | 小区详情 |
| 小区 | PATCH | `/communities/{id}/` | 已登录 + 业委会 | 更新小区 |
| 小区 | DELETE | `/communities/{id}/` | 已登录 + 业委会 | 删除小区 |
| 小区 | GET | `/communities/{id}/members/` | 已登录 + 业委会 | 小区成员列表（支持筛选） |
| 小区 | DELETE | `/communities/{id}/members/{user_id}/` | 已登录 + 业委会 | 删除小区成员 |
| 小区 | POST | `/communities/{id}/members/{user_id}/verify/` | 已登录 + 业委会 | 认证用户（通过审核） |
| 小区 | POST | `/communities/{id}/members/{user_id}/unverify/` | 已登录 + 业委会 | 取消用户认证 |
| 小区 | POST | `/communities/{id}/members/{user_id}/kick/` | 已登录 + 业委会 | 踢出用户（保留账号活跃） |
| 话题 | GET | `/topics/` | 已登录 | 话题列表（自动按用户小区筛选 + 游标分页，排除草稿） |
| 话题 | POST | `/topics/` | 已登录 + 已认证 | 创建话题（直接发布） |
| 话题 | POST | `/topics/draft/` | 已登录 | 获取或创建草稿话题 |
| 话题 | GET | `/topics/{id}/` | 已登录 | 话题详情 |
| 话题 | PATCH | `/topics/{id}/` | 业委会或作者 | 更新话题 |
| 话题 | DELETE | `/topics/{id}/` | 业委会或作者 | 删除话题（级联删除图片） |
| 话题 | POST | `/topics/{id}/publish/` | 已登录 + 作者 | 发布草稿话题 |
| 话题 | GET | `/topics/{id}/images/` | 已登录 | 获取话题图片列表 |
| 话题 | POST | `/topics/{id}/images/` | 已登录 + 作者 | 上传图片（multipart，≤500KB） |
| 话题 | DELETE | `/topics/{id}/images/{image_id}/` | 已登录 + 作者 | 删除单张图片 |
| 话题 | POST | `/topics/{id}/like/` | 已登录 + 已认证 | 点赞/取消点赞 |
| 话题 | POST | `/topics/{id}/subscribe/` | 已登录 + 已认证 | 订阅/取消订阅 |
| 话题 | POST | `/topics/{id}/read/` | 已登录 + 已认证 | 标记已读 |
| 话题 | GET | `/topics/{id}/comments/` | 已登录 | 获取评论列表 |
| 话题 | POST | `/topics/{id}/comments/` | 已登录 + 已认证 | 添加评论 |
| 话题 | POST | `/topics/{id}/pin/` | 已登录 + 业委会 | 置顶/取消置顶 |
| 话题 | POST | `/topics/{id}/hide/` | 已登录 + 业委会 | 隐藏/取消隐藏 |
| 话题 | POST | `/topics/{id}/close/` | 已登录 + 业委会 | 关闭/重新开启 |
| 邀请 | GET | `/invitations/` | 已登录 | 我的邀请记录 |
| 邀请 | POST | `/invitations/` | 已登录 | 记录邀请关系（传入 inviter user_id） |
| 邀请 | DELETE | `/invitations/{id}/` | 已登录 | 删除邀请记录 |

---

## 一、用户档案接口

---

### 1. 获取当前用户 Profile

**GET** `/users/me/`

**权限**: `IsAuthenticated`

**说明**: 返回当前用户在 neighbor_hub 应用中的完整 Profile，同时附带 `my_communities` 字段（当前用户创建的小区列表，含未激活的），用于中转站/等待审核页减少额外请求。

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
  "role": "owner|committee|property",
  "building": "1号楼",
  "bio": "个人简介",
  "join_note": "我是3号楼业主",
  "is_verified": true,
  "verified_at": "2026-07-19T10:00:00Z",
  "verification_note": "审核备注",
  "invited_by": "uuid-or-null",
  "invited_by_name": "张三",
  "is_active": true,
  "last_login_at": "2026-07-19T10:00:00Z",
  "created_at": "2026-07-19T10:00:00Z",
  "updated_at": "2026-07-19T10:00:00Z",
  "my_communities": [
    {
      "id": "uuid",
      "name": "阳光花园",
      "address": "北京市朝阳区xxx路100号",
      "description": "高品质住宅小区",
      "is_active": false,
      "established_at": "2015-06-01",
      "members_count": 0,
      "created_at": "2026-07-27T10:00:00Z",
      "updated_at": "2026-07-27T10:00:00Z"
    }
  ]
}
```

**`my_communities` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| my_communities | array | 当前用户创建的小区列表（含未激活的，按创建时间倒序） |

> **新增原因**：`WaitingVerificationPage` 原来需要每 5 秒轮询 `getMyProfile` + 额外调 `getCommunities({mine:true})` 查看创建申请状态。现在 `my_communities` 直接附带在 Profile 响应中，减少一个独立请求。

---

### 2. 获取当前用户统计

**GET** `/users/me/stats/`

> **v2.4.0 新增**

**权限**: `IsAuthenticated`

**功能说明**: 返回当前用户的聚合统计数据，用于个人中心页展示统计数字。避免前端拉取话题列表做计数。

**响应 (HTTP 200)**:
```json
{
  "topics_count": 12,
  "subscriptions_count": 5,
  "liked_count": 8,
  "read_count": 30
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| topics_count | int | 用户发起的非草稿话题数 |
| subscriptions_count | int | 用户订阅的话题数 |
| liked_count | int | 用户点赞过的话题数 |
| read_count | int | 用户已读的话题数 |

> **页面使用建议**：`ProfilePage` 的主接口改为 `getStats`，`updateProfile` 作为辅助接口，符合「一主 + 若干辅」原则。

---

### 3. 更新当前用户 Profile

**PATCH** `/users/me/`

**权限**: `IsAuthenticated`

**请求体**:
```json
{
  "nickname": "新昵称",
  "avatar": "https://example.com/avatar.jpg",
  "building": "2号楼",
  "bio": "我是小区热心业主",
  "join_note": "我是3号楼业主，请通过审核"
}
```

**可修改字段**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| nickname | string | 否 | 昵称（最大50字符） |
| avatar | string | 否 | 头像URL |
| building | string | 否 | 楼号（最大50字符） |
| bio | string | 否 | 个人简介（最大200字符） |
| join_note | string | 否 | 加入备注（最大255字符，审核前可修改） |

**系统保护字段**（通过 `read_only_fields` 保护，不可通过此接口修改）：

| 字段 | 保护原因 |
|------|----------|
| `role` | 角色管理需通过认证申请或管理后台设置 |
| `community` | 小区切换需使用专用接口 `/users/me/switch-community/` |
| `is_verified` | 认证状态需通过认证流程 |
| `verified_at` / `verified_by` / `verification_note` | 认证相关信息由系统管理 |
| `invited_by` | 邀请关系通过邀请流程自动设置 |
| `is_active` | 账号状态由管理系统管理 |

**响应 (HTTP 200)**: 更新后的 Profile 对象

---

### 4. 切换/退出小区

**POST** `/users/me/switch-community/`

**权限**: `IsAuthenticated`

**功能说明**:
- **传入 community UUID** → 切换/加入该小区，认证状态重置为未认证
- **不传 community 或传 null** → 退出当前小区，回到中转站
- 切换/退出后认证状态自动重置（`is_verified=False, role=owner`）
- 退出小区时同时清空 `building`、`join_note`、认证相关字段
- 可附带 `join_note` 加入备注，供业委会审核参考（仅切换时生效）

**请求体（切换小区）**:
```json
{
  "community": "目标小区UUID",
  "join_note": "我是3号楼业主，请通过审核"
}
```

**请求体（退出小区，回到中转站）**:
```json
{
  "community": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| community | UUID/null | 否 | 目标小区 ID（必须存在且已激活）；传 `null` 或不传表示退出当前小区 |
| join_note | string | 否 | 加入备注（最大255字符，供业委会审核参考，仅切换时生效） |

**响应 (HTTP 200) — 切换小区**:
```json
{
  "message": "小区切换成功",
  "data": { "...Profile对象" },
  "meta": {
    "old_community_name": "原小区名称",
    "was_verified": true,
    "old_role": "owner",
    "new_community_name": "新小区名称",
    "requires_reverification": true
  }
}
```

**响应 (HTTP 200) — 退出小区**:
```json
{
  "message": "已退出小区，回到中转站",
  "data": { "...Profile对象" },
  "meta": {
    "old_community_name": "原小区名称",
    "was_verified": false,
    "old_role": "owner",
    "new_community_name": null,
    "requires_reverification": true
  }
}
```

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 切换到当前小区 | `{"error": "您已经是该小区的成员"}` |
| 400 | 退出但当前无小区 | `{"error": "您当前不在任何小区中"}` |
| 400 | 小区参数校验失败 | `{"community": ["目标小区不存在"]}` |
| 400 | 小区未激活 | `{"community": ["目标小区未激活，无法加入"]}` |

---

### 5. 上传用户头像

**POST** `/users/me/avatar/`

**权限**: `IsAuthenticated`

**Content-Type**: `multipart/form-data`

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| avatar | file | 是 | 头像图片文件（≤500KB，支持 jpg/jpeg/png/webp/gif） |

**响应 (HTTP 200)**:
```json
{
  "avatar": "https://neighbor-hub.oss-cn-shanghai.aliyuncs.com/avatars/xxx/yyy.jpg",
  "message": "头像更新成功"
}
```

---

### 6. 查询用户档案（用于邀请功能）

**GET** `/users/profile/{user_id}/`

**权限**: `IsAuthenticated`

**功能说明**: 根据关联用户ID查询用户档案信息，主要用于邀请功能，仅返回公开信息。

**URL参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | UUID | 是 | 关联的用户 ID |

**响应 (HTTP 200)**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "nickname": "张三",
  "avatar": "https://example.com/avatar.jpg",
  "role": "owner",
  "role_display": "业主",
  "is_verified": true,
  "community": {
    "id": "uuid",
    "name": "阳光花园"
  },
  "building": "1号楼",
  "bio": "热爱社区生活",
  "member_since": "2024-01-15T10:30:00Z"
}
```

---

## 小区切换规则

### 规则说明

当用户切换小区时（通过 `/users/me/switch-community/`），系统执行以下逻辑：

| 原状态 | 切换后状态 | 说明 |
|--------|-----------|------|
| `is_verified=True, role=owner` | `is_verified=False, role=owner` | 认证自动失效 |
| `is_verified=True, role=committee` | `is_verified=False, role=owner` | 业委会身份不继承 |
| `is_verified=False, role=owner` | 保持不变 | 无影响 |

### 设计理由

1. **认证是小区对用户的认可**——A 小区的业主身份不代表自动获得 B 小区的身份
2. **保障小区安全**——新小区业委会有权审核每位新成员
3. **支持社区自然扩圈**——用户可自由加入新小区，只需重新走认证流程
4. **权益隔离**——旧小区的身份、权限不会自动带入新小区

---

## 中转站流程（无小区用户）

当用户注册时没有 `invited_by` 参数（非邀请注册），创建的 `NeighborHubProfile` 中 `community=null`，用户停留在中转站页面。

### 路径1：选择已有小区

```
1. GET /communities/                                → 已激活小区列表
2. POST /users/me/switch-community/                 → 选择小区 + 附带 join_note
   → community = 目标小区, is_verified = false
3. GET /users/me/                                    → 查看状态（含 my_communities）
   → community != null, is_verified = false → 展示"等待审核中"
   → community != null, is_verified = true  → 审核通过，进入小区首页
4. PATCH /users/me/                                  → 审核前可修改 join_note
5. POST /users/me/switch-community/                  → 可切换到其他小区
```

业委会审核入口：
```
GET /communities/{id}/members/?is_verified=false    → 待审核成员列表
POST /communities/{id}/members/{user_id}/verify/    → 通过审核
POST /communities/{id}/members/{user_id}/kick/      → 拒绝（打回中转站）
```

### 路径2：申请创建小区

```
1. POST /communities/                                → 创建小区（is_active=false）
2. GET /users/me/                                    → 返回值中 my_communities 含审核状态
   → my_communities[].is_active = false → 待审核
   → my_communities[].is_active = true  → 已通过
3. 小区激活后，走路径1选择该小区
```

> **优化说明**：路径2原需要独立调 `GET /communities/?mine=1` 查看审核状态，现在 `GET /users/me/` 的 `my_communities` 字段直接附带，轮询时无需额外请求。

---

## 二、小区接口

---

### 7. 小区列表

**GET** `/communities/`

**权限**: `IsAuthenticated`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mine | string | 否 | `1` 或 `true` 时仅返回当前用户创建的小区（含未激活的，用于查看创建审核进度） |

**访问规则**:

| 用户类型 | 默认（不传 mine） | `?mine=1` |
|----------|-------------------|----------|
| 普通用户 | 仅 `is_active=True` 的小区 | 自己创建的所有小区（含未激活） |
| 管理员（is_staff） | 所有小区 | 自己创建的所有小区 |

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

> **性能说明**: `members_count` 通过 SQL `COUNT` 注解实现，无 N+1 查询问题。

---

### 8. 创建小区

**POST** `/communities/`

**权限**: `IsAuthenticated`

**功能说明**:
- 任何已登录用户均可创建小区
- **非管理员**创建的小区 `is_active=False`，不会出现在公开小区列表中，需 admin 在 Django Admin 后台审核激活
- **管理员**（`is_staff=True`）创建的小区 `is_active=True`，直接生效
- `created_by` 自动设置为当前用户

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
| name | string | 是 | 小区名称（最大100字符） |
| address | string | 是 | 小区地址（最大255字符） |
| description | string | 否 | 小区描述 |
| established_at | date | 否 | 建成日期（格式：YYYY-MM-DD） |

**响应 (HTTP 201)**: 创建的小区详情

---

### 9. 小区详情

**GET** `/communities/{id}/`

**权限**: `IsAuthenticated`

**访问规则**:
- 已激活的小区（`is_active=True`）：所有用户可查看
- 未激活的小区（`is_active=False`）：仅创建者本人或管理员（`is_staff`）可查看

---

### 10. 更新小区

**PATCH** `/communities/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅本小区业委会）

> **安全规则**：业委会只能更新自己所属小区。非本小区的业委会访问会返回 404。

---

### 11. 删除小区

**DELETE** `/communities/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅本小区业委会）

**响应 (HTTP 204)**: No Content

---

### 12. 小区成员列表

**GET** `/communities/{id}/members/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅本小区业委会）

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_verified | boolean | 否 | 按认证状态筛选：`true` 已认证 / `false` 未认证 |
| role | string | 否 | 按角色筛选：`owner`/`committee`/`property` |

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
    "..."
  }
]
```

**说明**: 
- 仅返回 `is_active=true` 的活跃成员
- 不返回业委会成员（业委会由平台管理员审核，不出现在成员管理列表中）
- 非本小区业委会调用返回 404

---

### 13. 删除小区成员

**DELETE** `/communities/{id}/members/{user_id}/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅本小区业委会）

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

**响应 (HTTP 200)**:
```json
{
  "message": "成员已从小区移除"
}
```

---

### 14. 认证用户（通过审核）

**POST** `/communities/{id}/members/{user_id}/verify/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅本小区业委会）

**功能说明**: 将未认证用户设为已认证状态，与 `unverify` 互为逆操作。

**请求体**:
```json
{
  "role": "owner",
  "note": "审核通过，确认为业主"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role | string | 否 | 认证身份：`owner`（业主，默认）或 `property`（物业） |
| note | string | 否 | 审核备注（最大255字符） |

**响应 (HTTP 200)**:
```json
{
  "message": "已认证该成员"
}
```

---

### 15. 取消用户认证

**POST** `/communities/{id}/members/{user_id}/unverify/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅本小区业委会）

**功能说明**: 将已认证用户改回未认证状态，用户需重新提交认证申请。

**响应 (HTTP 200)**:
```json
{
  "message": "已取消用户认证"
}
```

---

### 16. 踢出用户

**POST** `/communities/{id}/members/{user_id}/kick/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅本小区业委会）

**功能说明**: 踢出用户（保留账号活跃，可加入其他小区）

与 DELETE（软删除）的区别：
- **kick**：`community=null, is_verified=false, role=owner, is_active=true` → 用户可重新选择其他小区
- **delete**：`is_active=false, nickname='已注销用户'` → 用户账号被软删除，无法再使用

用于审核人员拒绝待审核用户。

**响应 (HTTP 200)**:
```json
{
  "message": "已将用户移出阳光花园"
}
```

---

## 三、话题接口

---

### 17. 话题列表

**GET** `/topics/`

**权限**: `IsAuthenticated`

**说明**: 自动按当前登录用户的小区筛选，前端无需传 `community` 参数。支持游标分页。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| filter | string | 否 | 行为筛选：`all`（默认）/ `unread` / `read` / `liked` / `subscribed` / `mine` |
| category | string | 否 | 按分类筛选（见下方可选值），与 `filter` 可组合使用 |
| search | string | 否 | 搜索标题/内容（模糊匹配） |
| status | string | 否 | 状态筛选：`active`（默认）/ `hidden` / `closed` / `all`，后三个仅业委会可用 |
| cursor | string | 否 | 游标分页标记（首次请求不传，加载下一页时传入上次返回的 `next` 值） |
| page_size | int | 否 | 每页数量，默认 10，最大 50 |

**filter 可选值**:

| 值 | 说明 |
|----|------|
| `all` | 默认，全部话题（带已读/未读标记） |
| `unread` | 仅未读话题 |
| `read` | 仅已读话题 |
| `liked` | 我点赞过的话题 |
| `subscribed` | 我收藏的话题 |
| `mine` | **新增** 我发起的话题（筛选 `author = 当前用户`） |

> **新增 `mine` 取值**：用于 `SubscriptionsPage` 的「我的话题」Tab，后端直接筛选 `author=当前用户`，无需前端全量过滤。

**status 可选值**（业委会管理页用）:

| 值 | 说明 | 权限 |
|----|------|------|
| `active` | 默认，仅正常话题 | 所有用户 |
| `hidden` | 仅隐藏话题 | 仅业委会 |
| `closed` | 仅关闭话题 | 仅业委会 |
| `all` | 所有状态话题 | 仅业委会 |

> 非业委会用户传 `status=hidden/closed/all` 会返回 403。

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

**请求示例**:
```
# 默认：全部话题
GET /topics/

# 我发起的话题
GET /topics/?filter=mine

# 我收藏的话题
GET /topics/?filter=subscribed

# 未读 + 设施维修分类
GET /topics/?filter=unread&category=repair

# 加载下一页
GET /topics/?cursor=cD0yMDI2LTA3LTE5&page_size=10
```

**响应 (HTTP 200)**:
```json
{
  "results": [
    {
      "id": "uuid",
      "author": "uuid",
      "author_nickname": "张三",
      "author_building": "1号楼",
      "author_role": "owner",
      "title": "关于电梯维修的通知",
      "category": "notice",
      "has_image": false,
      "cover_image": null,
      "poster_style": "minimal",
      "likes_count": 5,
      "comments_count": 3,
      "views_count": 50,
      "subscriptions_count": 8,
      "readers_count": 42,
      "is_pinned": false,
      "status": "active",
      "is_liked": true,
      "is_subscribed": false,
      "is_read": false,
      "read_count": 0,
      "hot_comments": [
        {
          "id": "uuid",
          "author": "uuid",
          "author_nickname": "李四",
          "author_avatar": "https://...",
          "author_building": "3栋",
          "content": "支持！这个问题确实该解决了。",
          "likes_count": 12,
          "created_at": "2026-07-19T11:00:00Z"
        }
      ],
      "created_at": "2026-07-19T10:00:00Z",
      "published_at": "2026-07-19T11:00:00Z",
      "updated_at": null
    }
  ],
  "next": "cursor_string_for_next_page",
  "previous": null
}
```

---

### 18. 创建话题（直接发布，不推荐）

**POST** `/topics/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`（需已认证）

> **已被草稿流程取代**：推荐使用 `POST /topics/draft/` + `POST /topics/{id}/publish/` 的草稿流程，以便上传图片。此接口仍然可用，但创建的话题没有图片上传能力。

**请求体**:
```json
{
  "community": "uuid",
  "title": "关于小区绿化的建议",
  "content": "建议在小区增加一些绿植...",
  "category": "environment",
  "has_image": false,
  "poster_style": "minimal",
  "extra_data": {}
}
```

**响应 (HTTP 201)**: 创建的话题详情

---

### 19. 获取或创建草稿话题

**POST** `/topics/draft/`

**权限**: `IsAuthenticated`

**功能说明**:
- 前端进入「创建话题」页面时调用
- 如果当前用户在当前小区已有草稿话题，返回该草稿（含已上传图片列表）
- 如果没有草稿，创建一个新的草稿话题（`is_draft=True`）并返回
- 草稿话题不展示在信息流列表中
- 后端是唯一真相源，无需前端本地缓存

**请求体**: 无

**响应 (HTTP 200)**:
```json
{
  "id": "uuid",
  "is_draft": true,
  "title": "",
  "content": "",
  "category": "other",
  "has_image": false,
  "poster_style": "minimal",
  "images": [],
  "created_at": "2026-07-25T10:00:00Z",
  "published_at": null,
  "updated_at": null
}
```

---

### 20. 发布草稿话题

**POST** `/topics/{id}/publish/`

**权限**: `IsAuthenticated` + 话题作者本人

**功能说明**:
- 将草稿话题转为正式话题（`is_draft=False`），加入信息流
- 首次发布时设置 `published_at` 为当前时间
- 校验标题（≥2字符）和内容（非空）

**请求体**（可选）:
```json
{
  "title": "话题标题",
  "content": "话题内容",
  "category": "environment"
}
```

**响应 (HTTP 200)**: 发布后的话题详情（同话题详情格式）

---

### 21. 话题详情

**GET** `/topics/{id}/`

**权限**: `IsAuthenticated`

**说明**: 用于话题详情页，返回话题完整内容、统计数据和讨论区（评论树）。

**响应 (HTTP 200)**:
```json
{
  "id": "uuid",
  "author": "uuid",
  "author_nickname": "张三",
  "author_building": "1号楼",
  "author_role": "owner",
  "title": "关于电梯维修的通知",
  "category": "notice",
  "has_image": false,
  "poster_style": "minimal",
  "likes_count": 5,
  "comments_count": 3,
  "views_count": 50,
  "subscriptions_count": 8,
  "readers_count": 42,
  "is_pinned": false,
  "status": "active",
  "is_liked": true,
  "is_subscribed": false,
  "is_read": false,
  "read_count": 0,
  "hot_comments": [ "..." ],
  "content": "电梯维修通知全文内容...",
  "extra_data": {},
  "is_draft": false,
  "images": [
    {
      "id": "uuid",
      "topic": "uuid",
      "image_url": "https://...",
      "sort_order": 0,
      "created_at": "2026-07-19T10:00:00Z"
    }
  ],
  "comments": [
    {
      "id": "uuid",
      "author": "uuid",
      "author_nickname": "李四",
      "author_avatar": "https://...",
      "author_building": "3栋",
      "author_role": "owner",
      "parent": null,
      "content": "支持！",
      "likes_count": 12,
      "is_active": true,
      "replies_count": 2,
      "replies": [ "..." ],
      "created_at": "2026-07-19T11:00:00Z",
      "updated_at": "2026-07-19T11:00:00Z"
    }
  ],
  "created_at": "2026-07-19T10:00:00Z",
  "published_at": "2026-07-19T11:00:00Z",
  "updated_at": null
}
```

---

### 22. 更新话题

**PATCH** `/topics/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeOrAuthor`（业委会或作者）

**说明**: 编辑话题内容时，`updated_at` 自动设为当前时间。已关闭/已隐藏的话题不可编辑。

**响应 (HTTP 200)**: 更新后的话题详情

---

### 23. 删除话题

**DELETE** `/topics/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeOrAuthor`（业委会或作者）

**说明**: 删除时级联删除所有关联图片（CASCADE + pre_delete 信号自动清理 OSS）。已关闭/已隐藏的话题不可删除。

**响应 (HTTP 204)**: No Content

---

### 24. 话题图片管理

#### 获取图片列表

**GET** `/topics/{id}/images/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "topic": "uuid",
    "image_url": "https://...",
    "sort_order": 0,
    "created_at": "2026-07-25T10:00:00Z"
  }
]
```

#### 上传图片

**POST** `/topics/{id}/images/`

**权限**: `IsAuthenticated` + 话题作者本人

**Content-Type**: `multipart/form-data`

**上传约束**:

| 约束 | 规则 |
|------|------|
| 单张大小 | ≤ 500KB |
| 允许格式 | jpg、jpeg、png、webp、gif |
| 格式校验 | Pillow 读取文件头验证（防伪造扩展名） |
| 每话题数量 | ≤ 9 张 |

**响应 (HTTP 201)**:
```json
{
  "id": "uuid",
  "topic": "uuid",
  "image_url": "https://...",
  "sort_order": 0,
  "created_at": "2026-07-25T10:00:00Z"
}
```

#### 删除图片

**DELETE** `/topics/{id}/images/{image_id}/`

**权限**: `IsAuthenticated` + 话题作者本人

**功能说明**: 同步删除 OSS 文件和 DB 记录。如果删除后没有图片了，自动更新 `has_image=False`。

**响应 (HTTP 200)**:
```json
{
  "message": "图片已删除"
}
```

---

### 25. 点赞/取消点赞

**POST** `/topics/{id}/like/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**响应 (HTTP 200)**:
```json
{
  "liked": true,
  "likes_count": 6
}
```

---

### 26. 订阅/取消订阅

**POST** `/topics/{id}/subscribe/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**响应 (HTTP 200)**:
```json
{
  "subscribed": true
}
```

---

### 27. 标记已读

**POST** `/topics/{id}/read/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**说明**: 首次标记创建阅读记录，重复调用递增 `read_count`，同时递增话题的 `views_count`。

**响应 (HTTP 200)**:
```json
{
  "is_read": true,
  "read_count": 2,
  "views_count": 51
}
```

---

### 28. 评论管理

> **扁平化回复模型**：所有回复都直接挂在顶级评论下（`parent` 指向根评论），通过 `reply_to` 字段标记「这条回复是给谁的」。不支持多级嵌套，但支持任意用户之间的回复对话。
>
> 数据结构示意：
> ```
> 评论A (parent=null, reply_to=null)         — 张三发的顶级评论
>   ├─ 回复B (parent=A, reply_to=张三)        — 李四回复张三
>   ├─ 回复C (parent=A, reply_to=李四)        — 王五回复李四（次级回复）
>   └─ 回复D (parent=A, reply_to=王五)        — 赵六回复王五（次级回复）
> ```
> 前端渲染时，所有回复都在 A 的 `replies` 数组中平铺展示，通过 `reply_to_nickname` 显示「回复 @某用户」。

#### 获取评论列表

**GET** `/topics/{id}/comments/`

**权限**: `IsAuthenticated`

**说明**: 返回顶级评论（parent 为 null），每条评论包含 `replies` 嵌套回复列表（一级扁平化，所有回复都在根评论下）。

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "topic": "uuid",
    "author": "uuid",
    "author_nickname": "张三",
    "author_avatar": "头像URL",
    "author_building": "2号楼",
    "author_role": "owner",
    "parent": null,
    "reply_to": null,
    "reply_to_nickname": null,
    "content": "支持这个建议！",
    "likes_count": 2,
    "is_active": true,
    "replies_count": 2,
    "replies": [
      {
        "id": "uuid",
        "topic": "uuid",
        "author": "uuid",
        "author_nickname": "李四",
        "author_avatar": "头像URL",
        "author_building": "5栋",
        "author_role": "committee",
        "parent": "uuid-of-A",
        "reply_to": "uuid-of-张三",
        "reply_to_nickname": "张三",
        "content": "已安排处理",
        "likes_count": 1,
        "is_active": true,
        "replies_count": 0,
        "replies": [],
        "created_at": "2026-07-19T11:00:00Z",
        "updated_at": "2026-07-19T11:00:00Z"
      },
      {
        "id": "uuid",
        "topic": "uuid",
        "author": "uuid",
        "author_nickname": "王五",
        "author_avatar": "头像URL",
        "author_building": "3栋",
        "author_role": "owner",
        "parent": "uuid-of-A",
        "reply_to": "uuid-of-李四",
        "reply_to_nickname": "李四",
        "content": "谢谢业委会！",
        "likes_count": 0,
        "is_active": true,
        "replies_count": 0,
        "replies": [],
        "created_at": "2026-07-19T11:30:00Z",
        "updated_at": "2026-07-19T11:30:00Z"
      }
    ],
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
]
```

**回复字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| parent | UUID/null | 根评论 ID（顶级评论为 null，所有回复都指向根评论） |
| reply_to | UUID/null | 被回复的用户 ID（顶级评论为 null） |
| reply_to_nickname | string/null | 被回复用户的昵称（取自 NeighborHubProfile.nickname，回退到 username） |
| replies | array | 回复列表（扁平化，所有回复都在根评论下，不再嵌套） |

#### 添加评论

**POST** `/topics/{id}/comments/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**请求体**:
```json
{
  "content": "我也觉得应该这样",
  "parent": "被回复的评论ID-or-null"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | 是 | 评论内容（最大1000字符） |
| parent | UUID/null | 否 | 被回复的评论 ID（可以是顶级评论或某条回复） |

> **扁平化规范化**：后端自动处理 `parent` 的规范化：
> - 不传 `parent` → 创建顶级评论（`parent=null, reply_to=null`）
> - `parent` 指向顶级评论 → `parent` 保持不变，`reply_to` 设为该评论的作者
> - `parent` 指向某条回复 → `parent` 提升为根评论 ID，`reply_to` 设为被回复回复的作者
>
> 前端无需关心规范化逻辑，只需传被回复评论的 ID 即可。

**响应 (HTTP 201)**: 创建的评论详情（含 `reply_to` 和 `reply_to_nickname` 字段）

**说明**: 已关闭/已隐藏的话题不可评论。`author_building` 和 `author_role` 自动从 Profile 填充。

---

### 29. 置顶/取消置顶话题

**POST** `/topics/{id}/pin/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**响应 (HTTP 200)**:
```json
{
  "is_pinned": true
}
```

---

### 30. 隐藏/取消隐藏话题

**POST** `/topics/{id}/hide/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**功能说明**: 隐藏后话题不再出现在信息流列表中。再次调用可取消隐藏。

**响应 (HTTP 200)**:
```json
{
  "status": "hidden"
}
```

---

### 31. 关闭/重新开启话题

**POST** `/topics/{id}/close/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`

**功能说明**: 关闭后任何人不可编辑、删除、评论。再次调用可重新开启。

**响应 (HTTP 200)**:
```json
{
  "status": "closed"
}
```

---

## 四、邀请接口

> **H5 场景说明**：
> - **邀请链接格式**: `/auth?invited_by={user_id}`，**前端自行生成，后端不参与**
> - **邀请流程**：
>   1. 用户A（业主）分享链接给好友
>   2. 好友点击链接打开 H5 注册/登录
>   3. 前端检测到 URL 参数 `invited_by`，注册成功后调用 `POST /invitations/` 记录邀请关系

---

### 32. 我的邀请记录

**GET** `/invitations/`

**权限**: `IsAuthenticated`

**说明**: 返回当前用户作为邀请人或被邀请人的所有邀请记录

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 邀请记录 ID |
| inviter | UUID | 邀请人用户 ID |
| inviter_nickname | string | 邀请人昵称（取自 NeighborHubProfile.nickname，回退到 username） |
| inviter_community | UUID | 邀请人所属小区 ID |
| community_name | string/null | 邀请人小区名称 |
| invitee | UUID/null | 被邀请人用户 ID（未注册时为 null） |
| invitee_nickname | string/null | 被邀请人昵称（取自 NeighborHubProfile.nickname，回退到 username；未注册时为 null） |
| status | string | 邀请状态：`pending`/`accepted`/`expired`/`cancelled` |
| expires_at | datetime | 过期时间 |
| accepted_at | datetime/null | 接受时间 |
| created_at | datetime | 创建时间 |

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
    "invitee_nickname": "李四",
    "status": "accepted",
    "expires_at": "2026-08-18T10:00:00Z",
    "accepted_at": "2026-07-19T10:05:00Z",
    "created_at": "2026-07-19T10:05:00Z"
  }
]
```

---

### 33. 记录邀请关系

**POST** `/invitations/`

**权限**: `IsAuthenticated`

**请求体**:
```json
{
  "inviter": "邀请人 user_id"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| inviter | UUID | 是 | 邀请人的 user_id（从 URL 参数获取） |

**响应 (HTTP 201)**:
```json
{
  "id": "uuid",
  "inviter": "uuid",
  "inviter_nickname": "张三",
  "inviter_community": "uuid",
  "community_name": "阳光花园",
  "invitee": "uuid",
  "invitee_nickname": "李四",
  "status": "accepted",
  "expires_at": "2026-08-18T10:00:00Z",
  "accepted_at": "2026-07-19T10:05:00Z",
  "created_at": "2026-07-19T10:05:00Z"
}
```

---

### 34. 删除邀请记录

**DELETE** `/invitations/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 204)**: No Content

---

## 草稿话题与图片上传完整流程

```
1. 进入「创建话题」页面
   → POST /topics/draft/  →  返回 topic_id + 已有图片列表

2. 上传图片（可选，最多9张）
   → POST /topics/{topic_id}/images/  (multipart, ≤500KB)
   → 返回图片信息（id、image_url）

3. 删除图片（可选）
   → DELETE /topics/{topic_id}/images/{image_id}/

4. 更新标题/内容/分类
   → PATCH /topics/{topic_id}/  {"title": "...", "content": "...", "category": "..."}

5. 发布话题
   → POST /topics/{topic_id}/publish/  →  话题进入信息流

6. 关闭页面不保留草稿
   → DELETE /topics/{topic_id}/  →  级联删除草稿+图片（OSS+DB）
```

---

## 统一响应格式

### 成功响应

| 方法 | 状态码 |
|------|--------|
| GET / GET LIST | HTTP 200 |
| POST (创建成功) | HTTP 201 |
| PATCH (更新成功) | HTTP 200 |
| DELETE (删除话题) | HTTP 204（无返回体） |
| DELETE (删除图片) | HTTP 200（返回 `{"message": "图片已删除"}`） |
| POST (操作成功) | HTTP 200 |

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

## 页面接口使用总览

> 遵循设计原则：**一个页面一个主接口（核心数据）+ 若干接口配合（非核心数据）**

| 页面 | 主接口 | 辅助接口 | 评级 |
|------|--------|---------|------|
| `HomePage` | `getTopics`（游标分页） | `markTopicRead` / `likeTopic` / `subscribeTopic` / `addComment` | ✅ 合理 |
| `CreateTopicPage` | `createDraft` 或 `getTopic`（编辑） | `uploadTopicImage` / `deleteTopicImage` / `publishTopic` / `updateTopic` / `deleteTopic` | ✅ 合理 |
| `SubscriptionsPage` | `getTopics({filter:'subscribed'})` / `getTopics({filter:'mine'})` | `subscribeTopic` / `deleteTopic` | ✅ 已修复 |
| `ProfilePage` | `getStats` | `updateProfile` | ✅ 已修复 |
| `InvitePage` | `getInvitations` | 无 | ✅ 合理 |
| `TopicDetailPage` | `getTopic(id)`（含嵌套评论） | `likeTopic` / `subscribeTopic` / `addComment` / `pinTopic` / `hideTopic` / `closeTopic` | ✅ 合理 |
| `MembersPage` | `getCommunityMembers` | `verifyMember` / `kickMember` / `unverifyMember` | ✅ 合理 |
| `TopicManagementPage` | `getTopics({status})` | `pinTopic` / `hideTopic` / `closeTopic` | ✅ 合理 |
| `AuthPage` | `login` | `sendCode` | ✅ 合理 |
| `WaitingVerificationPage` | `refreshUser`（轮询，含 `my_communities`） | `getUserProfile` / `getCommunities` / `switchCommunity` | ✅ 已优化 |
| `CreateCommunityPage` | `createCommunity` | 无 | ✅ 合理 |
| `UpdateAvatarPage` | `uploadAvatar` | `refreshUser` | ✅ 合理 |

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| **v2.5.0** | 2026-07-27 | **新增** 扁平化回复模型：`Comment` 模型新增 `reply_to` 字段（回复目标用户）；`CommentSerializer` 新增 `reply_to` / `reply_to_nickname` 字段；POST 评论时后端自动规范化 `parent` 为根评论 + 设置 `reply_to`；所有回复平铺在根评论下，支持任意用户间回复对话；预取查询补充 `reply_to` 关联避免 N+1 |
| **v2.4.0** | 2026-07-27 | **新增** `GET /users/me/stats/` 用户聚合统计接口（ProfilePage 主接口）；**新增** `filter=mine` 话题筛选（SubscriptionsPage「我的话题」Tab）；`GET /users/me/` 返回值附带 `my_communities` 字段（减少 WaitingVerificationPage 额外请求）；`GET /invitations/` 响应增加 `invitee_nickname` 字段（被邀请人昵称）；**修复** CommunityViewSet 越权漏洞（业委会只能管理本小区）；**修复** CommunitySerializer N+1 查询（改用 annotate）；**修复** InvitationSerializer N+1 查询（select_related 预取双方 profile）；**优化** 删除 CurrentUserProfileView 重复定义；移除4处冗余手动权限检查；简化 NeighborHubProfileSerializer（read_only_fields 替代手动 update）；删除 CommunityViewSet 类级冗余 queryset |
| v2.3.0 | 2026-07-27 | 新增中转站流程；NeighborHubProfile 新增 `join_note` 字段；创建小区接口权限改为 `IsAuthenticated`；小区列表新增 `?mine=1` 查询参数 |
| v2.2.0 | 2026-07-27 | 新增 verify 认证用户接口；移除 VerificationRequest 和 AppNotification 模型 |
| v2.1.0 | 2026-07-25 | 用户头像上传接口；话题列表/详情返回 author_avatar/cover_image 字段 |
| v2.0.0 | 2026-07-25 | 图片上传功能：草稿话题机制；图片上传/列表/删除接口；TopicImage 模型 |
| v1.0.0 | 2026-07-19 | 初始版本 |
