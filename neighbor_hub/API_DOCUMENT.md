# NeighborHub API 接口文档

> **Base URL**: `http://your-domain.com/api/neighbor-hub/`  
> **认证方式**: JWT (Bearer Token)  
> **数据格式**: JSON  
> **最后更新时间**: 2026-07-25

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
| 邀请 | GET | `/invitations/` | 已登录 | 我的邀请记录 |
| 邀请 | POST | `/invitations/` | 已登录 | 记录邀请关系（传入 inviter user_id） |
| 邀请 | DELETE | `/invitations/{id}/` | 已登录 | 删除邀请记录 |

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
  "role": "owner|committee|property",
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
- 切换后认证状态自动重置为未认证（`is_verified=False, role=owner`）
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
    "role": "owner",
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
| `is_verified=True, role=owner` | `is_verified=False, role=owner` | 认证自动失效 |
| `is_verified=True, role=committee` | `is_verified=False, role=owner` | 业委会身份不继承 |
| `is_verified=False, role=owner` | 保持不变 | 无影响 |

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

### 5. 上传用户头像

**POST** `/users/me/avatar/`

**权限**: `IsAuthenticated`

**Content-Type**: `multipart/form-data`

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| avatar | file | ✅ | 头像图片文件（≤500KB，支持 jpg/jpeg/png/webp/gif） |

**功能说明**:
- 上传头像到 OSS，存储路径为 `avatars/{user_id}/{uuid}.{ext}`
- 更新 `NeighborHubProfile.avatar` 字段为新的图片 URL
- 如果已有旧头像，自动删除 OSS 中的旧头像文件

**响应 (HTTP 200)**:
```json
{
  "avatar": "https://neighbor-hub.oss-cn-shanghai.aliyuncs.com/avatars/xxx/yyy.jpg",
  "message": "头像更新成功"
}
```

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 未上传文件 | `{"avatar": "请选择要上传的图片"}` |
| 400 | 图片超过 500KB | `{"avatar": "图片大小不能超过 500KB（当前 xxxKB）"}` |
| 400 | 格式不支持 | `{"avatar": "不支持的图片格式..."}` |
| 404 | 用户档案不存在 | `{"error": "用户档案不存在"}` |
| 500 | OSS 上传失败 | `{"error": "头像上传失败，请稍后重试"}` |

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
| role | string | 否 | 按角色筛选：`owner`/`committee`/`property` |

**请求示例**:
```
GET /communities/{id}/members/?is_verified=false&role=owner
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

### 9b. 认证用户（通过审核）

**POST** `/communities/{id}/members/{user_id}/verify/`

**权限**: `IsAuthenticated` + `IsCommitteeMember`（仅业委会可操作）

**功能说明**:
将未认证用户设为已认证状态，与 `unverify` 互为逆操作。

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

**说明**:
- 认证后：`is_verified` 设为 `true`，`role` 设为指定身份，`verified_by` 设为当前操作者，`verified_at` 设为当前时间
- 不能认证已认证用户（返回 400）
- 不能认证其他业委会成员（返回 403）

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 用户已认证 | `{"error": "该用户已认证，无需重复认证"}` |
| 400 | role 值非法 | `{"error": "role 只能是 owner 或 property"}` |
| 400 | 用户不属于本小区 | `{"error": "该用户不属于本小区"}` |
| 403 | 无权限 | `{"error": "仅业委会成员可操作"}` |
| 403 | 认证业委会成员 | `{"error": "不能认证其他业委会成员"}` |
| 404 | 用户不存在 | `{"error": "用户不存在"}` |
| 404 | 非活跃成员 | `{"error": "该用户不是小区活跃成员"}` |

---

## 三、话题接口

---

### 10. 话题列表

**GET** `/topics/`

**权限**: `IsAuthenticated`

**说明**: 自动按当前登录用户的小区筛选，前端无需传 `community` 参数。支持游标分页。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| filter | string | 否 | 行为筛选：`all`（默认）/ `unread` / `read` / `liked` / `subscribed` |
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

# 未读 + 设施维修分类
GET /topics/?filter=unread&category=repair

# 搜索"电梯"关键词
GET /topics/?search=电梯

# 加载下一页（使用上次返回的 next 值）
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

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| results | array | 话题列表 |
| next | string\|null | 下一页游标（为 null 表示没有更多了） |
| previous | string\|null | 上一页游标 |
| published_at | string\|null | 首次发布时间（草稿时为 null） |
| updated_at | string\|null | 最后编辑时间（从未编辑时为 null） |
| created_at | string | 记录创建时间（草稿创建时间） |
| likes_count | int | 点赞数 |
| comments_count | int | 评论数 |
| views_count | int | 浏览量（每次标记已读时递增） |
| subscriptions_count | int | 订阅数（总订阅人数） |
| readers_count | int | 阅读数（总阅读人数） |
| is_liked | boolean | 当前用户是否已点赞 |
| is_subscribed | boolean | 当前用户是否已收藏 |
| is_read | boolean | 当前用户是否已读 |
| read_count | int | 当前用户的个人阅读次数（0=未读） |
| hot_comments | array | 3 条热门评论（按点赞数倒序） |
| author_avatar | string | 作者头像 URL（无头像时为空字符串） |
| has_image | boolean | 是否有配图 |
| cover_image | string\|null | 封面图 URL（第一张图片），无图时为 null |
| poster_style | string | 海报样式：gradient/emoji/minimal |

---

### 10b. 创建话题（直接发布，不推荐）

**POST** `/topics/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`（需已认证）

> **⚠️ 已被草稿流程取代**：推荐使用 `POST /topics/draft/` + `POST /topics/{id}/publish/` 的草稿流程，以便上传图片。
> 此接口仍然可用，但创建的话题没有图片上传能力。

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

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| community | UUID | ✅ | 所属小区 ID |
| title | string | ✅ | 话题标题（2-100字符） |
| content | string | ✅ | 话题内容 |
| category | string | 否 | 分类，默认 `other` |
| has_image | boolean | 否 | 是否有配图，默认 false |
| poster_style | string | 否 | 海报样式，默认 `minimal` |
| extra_data | object | 否 | 扩展数据 |

**响应 (HTTP 201)**: 创建的话题详情

**说明**: `author`、`author_building`、`author_role` 自动填充。

---

### 11. 话题详情

**GET** `/topics/{id}/`

**权限**: `IsAuthenticated`

**说明**: 用于话题详情页，返回话题完整内容、统计数据（阅读数/订阅数/点赞数）和讨论区（评论树）。

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
  "content": "电梯维修通知全文内容...",
  "extra_data": {},
  "is_draft": false,
  "images": [
    {
      "id": "uuid",
      "topic": "uuid",
      "image_url": "https://neighbor-hub.oss-cn-shanghai.aliyuncs.com/topics/xxx/yyy.jpg",
      "sort_order": 0,
      "created_at": "2026-07-19T10:00:00Z"
    }
  ],
  "comments": [
    {
      "id": "uuid",
      "topic": "uuid",
      "author": "uuid",
      "author_nickname": "李四",
      "author_avatar": "https://...",
      "author_building": "3栋",
      "author_role": "owner",
      "parent": null,
      "content": "支持！这个问题确实该解决了。",
      "likes_count": 12,
      "is_active": true,
      "replies_count": 2,
      "replies": [
        {
          "id": "uuid",
          "topic": "uuid",
          "author": "uuid",
          "author_nickname": "王五",
          "author_avatar": "https://...",
          "author_building": "5栋",
          "author_role": "committee",
          "parent": "uuid",
          "content": "已安排维修，预计明天完成",
          "likes_count": 3,
          "is_active": true,
          "replies_count": 0,
          "replies": [],
          "created_at": "2026-07-19T11:30:00Z",
          "updated_at": "2026-07-19T11:30:00Z"
        }
      ],
      "created_at": "2026-07-19T11:00:00Z",
      "updated_at": "2026-07-19T11:00:00Z"
    }
  ],
  "created_at": "2026-07-19T10:00:00Z",
  "published_at": "2026-07-19T11:00:00Z",
  "updated_at": null
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| content | string | 话题完整内容 |
| extra_data | object | 扩展数据 |
| is_draft | boolean | 是否为草稿（草稿不展示在信息流中） |
| images | array | 话题图片列表（含 id、image_url、thumbnail_url、sort_order、created_at） |
| published_at | string\|null | 首次发布时间（草稿时为 null） |
| updated_at | string\|null | 最后编辑时间（从未编辑时为 null） |
| created_at | string | 记录创建时间（草稿创建时间） |
| likes_count | int | 点赞数 |
| comments_count | int | 评论数 |
| views_count | int | 浏览量（每次标记已读时递增） |
| subscriptions_count | int | 订阅数（总订阅人数） |
| readers_count | int | 阅读数（总阅读人数） |
| is_liked | boolean | 当前用户是否已点赞 |
| is_subscribed | boolean | 当前用户是否已收藏 |
| is_read | boolean | 当前用户是否已读 |
| read_count | int | 当前用户的个人阅读次数（0=未读） |
| comments | array | 讨论区：顶级评论列表（含回复树） |
| comments[].replies | array | 该评论的回复列表（嵌套一层） |
| comments[].replies_count | int | 该评论的回复数 |
| hot_comments | array | 3 条热门评论（列表页用，详情页也有） |

---

### 12. 更新话题

**PATCH** `/topics/{id}/`

**权限**: `IsAuthenticated` + `IsCommitteeOrAuthor` 或 `IsCommitteeMember`

**说明**: 编辑话题内容时，`updated_at` 自动设为当前时间（`created_at` 和 `published_at` 不变）。

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

**说明**: 再次调用可取消订阅。订阅的话题会出现在用户的收藏列表中。

---

### 16. 标记已读

**POST** `/topics/{id}/read/`

**权限**: `IsAuthenticated` + `IsVerifiedUser`

**说明**: 前端在用户划过话题卡片或进入详情页时调用。首次标记创建阅读记录，重复调用递增 `read_count`，同时递增话题的 `views_count`（总浏览量）。

**响应 (HTTP 200)**:
```json
{
  "is_read": true,
  "read_count": 2,
  "views_count": 51
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| is_read | boolean | 始终为 true |
| read_count | int | 当前用户的个人阅读次数（1=首次阅读，2+ = 重复阅读） |
| views_count | int | 话题总浏览量（递增后） |

---

### 17. 获取评论列表

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
    "replies": [
      {
        "id": "uuid",
        "topic": "uuid",
        "author": "uuid",
        "author_nickname": "王五",
        "author_avatar": "头像URL",
        "author_building": "5栋",
        "author_role": "committee",
        "parent": "uuid",
        "content": "已安排处理",
        "likes_count": 1,
        "is_active": true,
        "replies_count": 0,
        "replies": [],
        "created_at": "2026-07-19T11:00:00Z",
        "updated_at": "2026-07-19T11:00:00Z"
      }
    ],
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T10:00:00Z"
  }
]
```

**说明**: 返回顶级评论（parent 为 null），每条评论包含 `replies` 嵌套回复列表（一级）。

---

### 18. 添加评论

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

### 19. 置顶/取消置顶话题

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

### 20. 获取或创建草稿话题

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

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 草稿话题 ID（后续上传图片/发布时使用） |
| is_draft | boolean | 始终为 true |
| published_at | null | 草稿未发布，始终为 null |
| updated_at | null | 草稿未编辑过，始终为 null |
| created_at | string | 草稿创建时间 |
| title | string | 草稿标题（初始为空） |
| content | string | 草稿内容（初始为空） |
| category | string | 分类（默认 other） |
| has_image | boolean | 是否有图片 |
| poster_style | string | 海报样式 |
| images | array | 已上传图片列表（含 id、image_url、sort_order、created_at） |

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 用户未加入小区 | `{"error": "请先加入小区"}` |

---

### 21. 发布草稿话题

**POST** `/topics/{id}/publish/`

**权限**: `IsAuthenticated` + 话题作者本人

**功能说明**:
- 将草稿话题转为正式话题（`is_draft=False`），加入信息流
- 首次发布时设置 `published_at` 为当前时间
- `created_at` 保持不变（草稿创建时间），`updated_at` 保持 null（未编辑）
- 校验标题（≥2字符）和内容（非空）

**请求体**（可选）:
```json
{
  "title": "话题标题",
  "content": "话题内容",
  "category": "environment"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | 话题标题（≥2字符，如未传则使用草稿已有值） |
| content | string | 否 | 话题内容（非空，如未传则使用草稿已有值） |
| category | string | 否 | 分类，如未传则使用草稿已有值 |

**响应 (HTTP 200)**: 发布后的话题详情（同 [话题详情](#11-话题详情) 格式）

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 不是草稿话题 | `{"error": "该话题不是草稿，无需发布"}` |
| 400 | 标题不足2字符 | `{"title": "标题至少需要2个字符"}` |
| 400 | 内容为空 | `{"content": "内容不能为空"}` |
| 403 | 非话题作者 | `{"error": "仅话题作者可发布"}` |

---

### 22. 获取话题图片列表

**GET** `/topics/{id}/images/`

**权限**: `IsAuthenticated`

**响应 (HTTP 200)**:
```json
[
  {
    "id": "uuid",
    "topic": "uuid",
    "image_url": "https://neighbor-hub.oss-cn-shanghai.aliyuncs.com/topics/xxx/yyy.jpg",
    "sort_order": 0,
    "created_at": "2026-07-25T10:00:00Z"
  }
]
```

---

### 23. 上传话题图片

**POST** `/topics/{id}/images/`

**权限**: `IsAuthenticated` + 话题作者本人

> **域名说明**: 返回的 `image_url` 域名由后端 OSS 配置决定，前端直接使用该字段即可，不要硬编码域名。

**Content-Type**: `multipart/form-data`

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| image | file | ✅ | 图片文件（multipart 上传） |

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
  "image_url": "https://neighbor-hub.oss-cn-shanghai.aliyuncs.com/topics/xxx/yyy.jpg",
  "sort_order": 0,
  "created_at": "2026-07-25T10:00:00Z"
}
```

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 400 | 未上传文件 | `{"image": "请选择要上传的图片"}` |
| 400 | 图片超过 500KB | `{"image": "图片大小不能超过 500KB（当前 xxxKB）"}` |
| 400 | 格式不支持 | `{"image": "不支持的图片格式：.bmp，仅允许 jpg, jpeg, png, webp, gif"}` |
| 400 | 文件内容与扩展名不匹配 | `{"image": "文件内容与扩展名不匹配（文件实际格式: PNG）"}` |
| 400 | 图片数量超过 9 张 | `{"error": "该话题已有 9 张图片，最多 9 张"}` |
| 403 | 非话题作者 | `{"error": "仅话题作者可上传图片"}` |
| 500 | OSS 上传失败 | `{"error": "图片上传失败，请稍后重试"}` |

---

### 24. 删除话题图片

**DELETE** `/topics/{id}/images/{image_id}/`

**权限**: `IsAuthenticated` + 话题作者本人

**功能说明**:
- 同步删除 OSS 上的文件和 DB 记录
- 如果删除后该话题没有图片了，自动更新 `has_image=False`

**响应 (HTTP 200)**:
```json
{
  "message": "图片已删除"
}
```

**错误响应**:

| HTTP | 场景 | 响应 |
|------|------|------|
| 403 | 非话题作者 | `{"error": "仅话题作者可删除图片"}` |
| 404 | 图片不存在 | `{"error": "图片不存在"}` |

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

## 四、邀请接口

> **H5 场景说明**：
> - **邀请链接格式**: `/join?inviter={user_id}`，**前端自行生成，后端不参与**
> - **邀请流程**:
>   1. 用户A（业主）分享链接给好友
>   2. 好友点击链接打开 H5 注册/登录
>   3. 前端检测到 URL 参数 `inviter`，注册成功后调用 `POST /invitations/` 记录邀请关系

---

### 20. 我的邀请记录

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

### 21. 记录邀请关系

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

### 22. 删除邀请记录

**DELETE** `/invitations/{id}/`

**权限**: `IsAuthenticated`

**响应 (HTTP 204)**: No Content

---

## 统一响应格式

### 成功响应

- GET/GET LIST: `HTTP 200`
- POST (创建成功): `HTTP 201`
- PATCH (更新成功): `HTTP 200`
- DELETE (删除话题): `HTTP 204`（无返回体）
- DELETE (删除图片): `HTTP 200`（返回 `{"message": "图片已删除"}`）
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

**创建话题（含图片）流程:**
```
1. 进入「创建话题」页面
   → POST /api/neighbor-hub/topics/draft/ → 获取草稿 topic_id + 已有图片
2. 上传图片（可选，最多9张）
   → POST /api/neighbor-hub/topics/{topic_id}/images/ (FormData, ≤500KB)
   → 返回 { id, image_url, sort_order }
3. 删除图片（可选）
   → DELETE /api/neighbor-hub/topics/{topic_id}/images/{image_id}/
4. 更新标题/内容/分类
   → PATCH /api/neighbor-hub/topics/{topic_id}/ { title, content, category }
5. 发布话题
   → POST /api/neighbor-hub/topics/{topic_id}/publish/ → 话题进入信息流
6. 关闭页面不保留草稿
   → DELETE /api/neighbor-hub/topics/{topic_id}/ → 级联删除草稿+图片
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

// ==================== 用户头像 ====================

// 上传用户头像（multipart/form-data）
const uploadAvatar = async (file) => {
  const formData = new FormData()
  formData.append('avatar', file)
  const { data } = await axios.post('/api/neighbor-hub/users/me/avatar/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
  // { avatar: 'https://...', message: '头像更新成功' }
}

// ==================== 话题相关 ====================

// 获取或创建草稿话题（进入创建话题页面时调用）
const getOrCreateDraft = async () => {
  const { data } = await axios.post('/api/neighbor-hub/topics/draft/')
  return data
  // { id, is_draft: true, title, content, category, has_image, images: [...], ... }
}

// 更新草稿内容（标题/内容/分类）
const updateDraft = async (topicId, { title, content, category }) => {
  const { data } = await axios.patch(`/api/neighbor-hub/topics/${topicId}/`, {
    title, content, category
  })
  return data
}

// 发布草稿话题
const publishTopic = async (topicId, { title, content, category } = {}) => {
  const { data } = await axios.post(`/api/neighbor-hub/topics/${topicId}/publish/`, {
    title, content, category  // 可选，如已通过 PATCH 更新过可不传
  })
  return data
}

// 直接创建话题（无图片场景）
const createTopic = async (topicData) => {
  const { data } = await axios.post('/api/neighbor-hub/topics/', topicData)
  return data
}

// ==================== 图片上传相关 ====================

// 上传单张图片（multipart/form-data）
const uploadTopicImage = async (topicId, file) => {
  const formData = new FormData()
  formData.append('image', file)
  const { data } = await axios.post(
    `/api/neighbor-hub/topics/${topicId}/images/`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return data
  // { id, topic, image_url, sort_order, created_at }
}

// 获取话题图片列表
const getTopicImages = async (topicId) => {
  const { data } = await axios.get(`/api/neighbor-hub/topics/${topicId}/images/`)
  return data
  // [ { id, topic, image_url, sort_order, created_at }, ... ]
}

// 删除单张图片
const deleteTopicImage = async (topicId, imageId) => {
  const { data } = await axios.delete(
    `/api/neighbor-hub/topics/${topicId}/images/${imageId}/`
  )
  return data
  // { message: '图片已删除' }
}

// ==================== 其他接口 ====================

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

// 点赞话题
const likeTopic = async (topicId) => {
  const { data } = await axios.post(`/api/neighbor-hub/topics/${topicId}/like/`)
  return data // { liked: true/false, likes_count: 6 }
}
```

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v2.2.0 | 2026-07-27 | 新增 POST `/communities/{id}/members/{user_id}/verify/` 认证用户接口（与 unverify 互逆）；移除 VerificationRequest 和 AppNotification 模型及相关接口 |
| v2.1.0 | 2026-07-25 | 用户头像上传接口（POST /users/me/avatar/）；话题列表/详情返回 author_avatar 字段；话题列表返回 cover_image 字段（封面图 URL）；删除重复的 patch 方法 |
| v2.0.0 | 2026-07-25 | 图片上传功能：新增草稿话题机制（POST /topics/draft/、POST /topics/{id}/publish/）；新增图片上传/列表/删除接口（基于阿里云 OSS）；新增 TopicImage 模型；Topic 移除 image_url 字段，改为多图模型；列表页排除草稿话题；详情页返回 images 字段 |
| v1.5.0 | 2026-07-23 | 话题详情接口优化：修复 500 错误（Coalesce+Subquery）；新增 `subscriptions_count`（订阅数）、`readers_count`（阅读数）字段；修复 `author_nickname`/`author_avatar` 从 NeighborHubProfile 获取（v1.4.0 重构遗留）；详情页返回评论树（含 replies 嵌套）；评论列表接口增加 replies 嵌套；`read` 接口递增 `views_count` 并返回；详情页不再受列表筛选参数影响 |
| v1.4.0 | 2026-07-20 | 用户模型重构：User 只负责基础认证（phone/email/username+password）；nickname、avatar 移至 NeighborHubProfile（应用专属）；UserAppProfile 作为应用标记，业委会可删除应用标记禁用用户访问 |
| v1.3.0 | 2026-07-20 | 邀请系统重构：移除邀请码机制，改为链接+二维码模式；前端生成邀请链接 `/join?inviter={user_id}`；后端只负责记录邀请关系 `POST /invitations/ {"inviter": "xxx"}`；过期时间调整为30天 |
| v1.2.0 | 2026-07-19 | 新增 POST `/users/me/switch-community/` 小区切换接口；新增业委会权限管理规则 |
| v1.1.0 | 2026-07-19 | 新增小区切换规则：切换小区后认证自动失效，需重新认证 |
| v1.0.0 | 2026-07-19 | 初始版本，包含完整的社区治理功能模块 |
