# Neighbor Hub API 接口文档

> **Base URL**: `http://your-domain.com/api/neighbor-hub/`  
> **认证方式**: JWT (Bearer Token)  
> **最后更新时间**: 2026-07-19

---

## � 认证说明

本服务采用 **JWT Token** 认证。登录后获取 `access` 和 `refresh` 两个 Token。

### 请求头格式

```
Authorization: Bearer <access_token>
```

### Token 有效期

| Token 类型 | 有效期 |
|-----------|--------|
| Access Token | 30 分钟 |
| Refresh Token | 7 天 |

### Token 刷新策略

- Access Token 过期后，使用 Refresh Token 刷新获取新的 Token
- Refresh Token 同时轮换，旧的加入黑名单
- Refresh Token 过期后需要重新登录

---

## 📋 权限层级

| 角色 | 标识 | 权限说明 |
|------|------|----------|
| 未登录 | - | 无法访问任何接口 |
| 已登录未认证 | `is_verified=false` | 仅查看，不能发帖/评论/点赞 |
| 已认证业主 | `role=owner` | 发帖、评论、点赞、订阅 |
| 业委会 | `role=committee` | 包含业主权限 + 审核、置顶、管理小区 |
| 物业 | `role=property` | 待定（保留角色） |

---

## � 公开接口（无需登录）

> 这些接口位于 `/api/auth/` 路径下，用于身份验证

---

### 1. 发送短信验证码

**POST** `/api/auth/sms/send/`

请求体：
```json
{
  "phone": "13800138000",
  "purpose": "register"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✅ | 手机号（11位） |
| purpose | string | ✅ | 用途：`register` / `login` / `reset_password` / `bind_phone` |

响应：
```json
{
  "message": "验证码已发送",
  "debug_code": "123456"
}
```

> ⚠️ `debug_code` 仅在开发环境返回，生产环境需实际发送短信

**限流**：同一手机号 60 秒内只能发送一次

---

### 2. 手机号 + 验证码登录

**POST** `/api/auth/auth/phone-login/`

请求体：
```json
{
  "phone": "13800138000",
  "code": "123456",
  "app_name": "neighbor_hub"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✅ | 手机号 |
| code | string | ✅ | 6位验证码 |
| app_name | string | 否 | 应用标识，默认为空 |

响应：
```json
{
  "user": {
    "id": "uuid",
    "nickname": "用户昵称",
    "phone": "138****8000",
    "avatar": "头像URL",
    "is_new_user": true
  },
  "access": "eyJ...",
  "refresh": "eyJ...",
  "expires_in": 1800
}
```

> 自动注册：如果没有该手机号的账户，会自动创建新用户并登录

---

### 3. 手机号注册

**POST** `/api/auth/auth/register/`

请求体：
```json
{
  "phone": "13800138000",
  "code": "123456",
  "nickname": "用户昵称",
  "app_name": "neighbor_hub"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✅ | 手机号（需未被注册） |
| code | string | ✅ | 6位验证码 |
| nickname | string | 否 | 用户昵称 |
| app_name | string | 否 | 应用标识 |

响应（HTTP 201）：
```json
{
  "user": {
    "id": "uuid",
    "nickname": "用户昵称",
    "phone": "138****8000",
    "avatar": "头像URL"
  },
  "access": "eyJ...",
  "refresh": "eyJ...",
  "expires_in": 1800
}
```

> 如果手机号已注册，返回 400 错误

---

### 4. 微信登录（预留）

**POST** `/api/auth/auth/wechat-login/`

请求体：
```json
{
  "code": "wx.login返回的code",
  "app_name": "neighbor_hub",
  "extra_data": {"nickname": "", "avatar": ""}
}
```

---

### 5. 刷新 Token

**POST** `/api/auth/auth/refresh/`

请求体：
```json
{
  "refresh": "eyJ..."
}
```

响应：
```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

---

### 6. 登出

**POST** `/api/auth/auth/logout/`

需要认证：✅

请求体：
```json
{
  "refresh": "eyJ..."
}
```

> 将 Refresh Token 加入黑名单使其失效

---

## �️ 用户档案

### 获取/更新当前用户 Profile

| 方法 | 路径 | 权限 |
|------|------|------|
| GET | `/api/neighbor-hub/users/me/` | 已登录 |
| PATCH | `/api/neighbor-hub/users/me/` | 已登录 |

**Profile 数据结构**：

```json
{
  "id": "档案UUID",
  "user_id": "用户UUID",
  "nickname": "用户昵称",
  "phone": "138****8000",
  "community": "小区UUID",
  "community_name": "幸福小区",
  "role": "owner",
  "building": "3号楼",
  "bio": "个人简介",
  "is_verified": true,
  "verified_at": "2026-07-19T10:00:00Z",
  "verification_note": "",
  "invited_by": "邀请人UUID",
  "is_active": true,
  "last_login_at": "2026-07-19T12:00:00Z",
  "created_at": "2026-07-01T08:00:00Z",
  "updated_at": "2026-07-19T12:00:00Z"
}
```

**role 枚举值**：
- `owner` - 业主
- `committee` - 业委会
- `property` - 物业
- `unverified` - 待认证

**PATCH 可修改字段**：仅 `building` 和 `bio`

---

## �️ 小区管理

### 小区列表

**GET** `/api/neighbor-hub/communities/`

权限：已登录

响应：
```json
[
  {
    "id": "小区UUID",
    "name": "幸福小区",
    "address": "北京市朝阳区xxx街道",
    "description": "小区描述",
    "is_active": true,
    "established_at": "2020-01-01",
    "members_count": 156,
    "created_at": "2026-07-01T08:00:00Z",
    "updated_at": "2026-07-19T12:00:00Z"
  }
]
```

### 小区详情

**GET** `/api/neighbor-hub/communities/{id}/`

权限：已登录

### 创建小区

**POST** `/api/neighbor-hub/communities/`

权限：业委会 (`role=committee`)

请求体：
```json
{
  "name": "幸福小区",
  "address": "北京市朝阳区xxx街道",
  "description": "小区描述",
  "established_at": "2020-01-01",
  "extra_data": {}
}
```

### 更新小区

**PATCH** `/api/neighbor-hub/communities/{id}/`

权限：业委会

### 删除小区

**DELETE** `/api/neighbor-hub/communities/{id}/`

权限：业委会

### 获取小区成员列表

**GET** `/api/neighbor-hub/communities/{id}/members/`

权限：已登录

---

## � 话题管理

### 话题列表

**GET** `/api/neighbor-hub/topics/`

权限：已登录

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| community | string | 按小区UUID筛选 |
| category | string | 按分类筛选 |
| status | string | 状态筛选，默认 `active` |
| search | string | 搜索标题/内容 |

**category 枚举值**：

| 值 | 说明 |
|-----|------|
| facility | 设施改造 |
| notice | 物业通知 |
| neighbor | 邻里关系 |
| environment | 环境治理 |
| repair | 设施维修 |
| help | 邻里互助 |
| announcement | 业委会公告 |
| activity | 社区活动 |
| dispute | 邻里纠纷 |
| other | 其他 |

响应：
```json
[
  {
    "id": "话题UUID",
    "community": "小区UUID",
    "community_name": "幸福小区",
    "author": "作者UUID",
    "author_nickname": "张三",
    "author_building": "3号楼",
    "author_role": "owner",
    "title": "关于小区健身器材更新的讨论",
    "category": "facility",
    "has_image": true,
    "image_url": "https://...",
    "poster_style": "gradient",
    "likes_count": 23,
    "comments_count": 8,
    "views_count": 156,
    "status": "active",
    "is_pinned": true,
    "is_liked": false,
    "is_subscribed": false,
    "created_at": "2026-07-19T10:00:00Z",
    "updated_at": "2026-07-19T12:00:00Z"
  }
]
```

### 话题详情

**GET** `/api/neighbor-hub/topics/{id}/`

权限：已登录

与列表字段相同，额外包含：
- `content` - 话题完整内容
- `extra_data` - 扩展数据
- `comments` - 评论列表（嵌套）

### 创建话题

**POST** `/api/neighbor-hub/topics/`

权限：已认证业主 (`is_verified=true`)

请求体：
```json
{
  "community": "小区UUID",
  "title": "标题（2-100字）",
  "content": "正文内容",
  "category": "facility",
  "has_image": false,
  "image_url": "",
  "poster_style": "minimal",
  "extra_data": {}
}
```

**poster_style**: `gradient` / `emoji` / `minimal`

### 更新话题

**PATCH** `/api/neighbor-hub/topics/{id}/`

权限：作者本人 或 业委会

### 删除话题

**DELETE** `/api/neighbor-hub/topics/{id}/`

权限：作者本人 或 业委会

---

## 💰 话题互动

### 点赞/取消点赞

**POST** `/api/neighbor-hub/topics/{id}/like/`

权限：已认证业主

响应：
```json
{
  "liked": true,
  "likes_count": 24
}
```

> 重复调用会切换点赞状态

### 订阅/取消订阅

**POST** `/api/neighbor-hub/topics/{id}/subscribe/`

权限：已认证业主

响应：
```json
{
  "subscribed": true
}
```

### 评论区

**GET** `/api/neighbor-hub/topics/{id}/comments/`

权限：已登录

获取顶级评论列表（不含回复）

**POST** `/api/neighbor-hub/topics/{id}/comments/`

权限：已认证业主

请求体：
```json
{
  "content": "评论内容（最多1000字）",
  "parent": "父评论UUID（可选，用于楼中楼回复）"
}
```

响应（HTTP 201）：
```json
{
  "id": "评论UUID",
  "topic": "话题UUID",
  "author": "作者UUID",
  "author_nickname": "张三",
  "author_avatar": "头像URL",
  "author_building": "3号楼",
  "author_role": "owner",
  "parent": null,
  "content": "评论内容",
  "likes_count": 0,
  "is_active": true,
  "replies_count": 0,
  "created_at": "2026-07-19T12:00:00Z",
  "updated_at": "2026-07-19T12:00:00Z"
}
```

---

## � 置顶管理

### 置顶/取消置顶话题

**POST** `/api/neighbor-hub/topics/{id}/pin/`

权限：业委会

响应：
```json
{
  "is_pinned": true
}
```

---

## 📩 邀请管理

### 我的邀请记录

**GET** `/api/neighbor-hub/invitations/`

权限：已登录

响应：
```json
[
  {
    "id": "邀请UUID",
    "inviter": "邀请人UUID",
    "inviter_nickname": "张三",
    "inviter_community": "小区UUID",
    "community_name": "幸福小区",
    "invitee_phone": "13900139000",
    "invitee_name": "李四",
    "code": "AB12CD34",
    "status": "pending",
    "expires_at": "2026-07-26T12:00:00Z",
    "accepted_at": null,
    "created_at": "2026-07-19T12:00:00Z"
  }
]
```

**status 枚举**：`pending` / `accepted` / `expired` / `cancelled`

### 创建邀请

**POST** `/api/neighbor-hub/invitations/`

权限：已登录（自动关联当前用户和小区）

请求体：
```json
{
  "invitee_phone": "13900139000",
  "invitee_name": "李四（可选）"
}
```

> 系统自动生成 8 位邀请码，有效期 7 天

### 验证邀请码

**POST** `/api/neighbor-hub/invitations/verify/`

权限：已登录

请求体：
```json
{
  "code": "AB12CD34"
}
```

响应：
```json
{
  "valid": true,
  "community_name": "幸福小区",
  "inviter_name": "张三"
}
```

---

## � 身份认证

### 提交认证申请

**POST** `/api/neighbor-hub/verification-requests/`

权限：已登录

请求体：
```json
{
  "community": "小区UUID",
  "name": "真实姓名",
  "phone": "13800138000",
  "building": "3号楼2单元101"
}
```

### 查看我的认证申请

**GET** `/api/neighbor-hub/verification-requests/`

权限：已登录

### 查看待审核列表（业委会）

**GET** `/api/neighbor-hub/verification-requests/pending/`

权限：业委会（仅查看其所在小区的待审核申请）

### 审核认证申请

**POST** `/api/neighbor-hub/verification-requests/{id}/review/`

权限：业委会

请求体：
```json
{
  "action": "approve",
  "note": "审核备注（可选）"
}
```

| action | 说明 |
|--------|------|
| approve | 通过认证 |
| reject | 拒绝认证 |

> 审核通过会自动将用户标记为已认证（`is_verified=true`），并发送通知给申请者

---

## 🔔 通知中心

### 通知列表

**GET** `/api/neighbor-hub/notifications/`

权限：已登录

响应：
```json
[
  {
    "id": "通知UUID",
    "type": "verification",
    "title": "身份认证已通过",
    "content": "恭喜！您已成为业主",
    "related_id": "关联资源UUID",
    "is_read": false,
    "read_at": null,
    "created_at": "2026-07-19T12:00:00Z"
  }
]
```

**type 枚举**：

| 值 | 说明 |
|-----|------|
| system | 系统通知 |
| topic_reply | 话题回复 |
| topic_like | 话题点赞 |
| verification | 认证通知 |
| invitation | 邀请通知 |

### 未读通知数量

**GET** `/api/neighbor-hub/notifications/unread-count/`

权限：已登录

响应：
```json
{
  "unread_count": 5
}
```

### 标记单条通知已读

**POST** `/api/neighbor-hub/notifications/{id}/read/`

权限：已登录

响应：
```json
{
  "read": true
}
```

### 全部标记已读

**POST** `/api/neighbor-hub/notifications/read-all/`

权限：已登录

---

## 📊 统一响应格式

### 成功响应

```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### 错误响应

```json
{
  "error": "错误描述信息"
}
```

或字段级错误：
```json
{
  "field_name": ["错误信息1", "错误信息2"]
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证（Token 无效或缺失） |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

---

## 🔧 前端对接建议

### 1. Axios 拦截器配置

```javascript
// 请求拦截器 - 自动添加 Token
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - 处理 401 错误
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/auth/auth/refresh/', { refresh })
          localStorage.setItem('access_token', data.access)
          localStorage.setItem('refresh_token', data.refresh)
          // 重试原请求
          error.config.headers.Authorization = `Bearer ${data.access}`
          return axios(error.config)
        } catch {
          // Refresh 也过期了，跳登录页
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
```

### 2. 权限判断

```javascript
// 检查当前用户是否有发帖权限
const canPostTopic = () => {
  const profile = store.state.userProfile
  return profile?.is_verified === true
}

// 检查是否为业委会
const isCommittee = () => {
  const profile = store.state.userProfile
  return profile?.role === 'committee'
}
```

### 3. 登录流程

```
1. POST /api/auth/sms/send/   → 发送验证码
2. POST /api/auth/auth/phone-login/  → 登录获取 Token
3. GET /api/neighbor-hub/users/me/  → 获取用户档案
4. 根据 profile.is_verified 控制发帖功能显示
```

---

## 📝 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-07-19 | 初始版本，包含用户、小区、话题、认证、通知模块 |
