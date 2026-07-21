# Users 应用 API 文档

**版本**: v1.0.0  
**基础路径**: `/api/users/`  
**认证方式**: JWT (Bearer Token)

---

## 概述

`users` 应用负责**统一用户认证**，仅处理基础注册、登录认证（手机号验证码），通过 `UserAppProfile` 实现多应用数据隔离。

各应用的业务资料（昵称、头像、小区、角色等）由各自的 Profile 模型管理。

**💡 新增特性**：当使用 `app_name=neighbor_hub` 登录时，系统会自动创建基础 `NeighborHubProfile` 档案，用户无需额外调用接口创建。

- 自动创建的档案默认角色为 **业主 (OWNER)**
- 用户的认证状态默认为 **未认证**，需要通过认证流程获得正式身份

---

## 通用说明

### 请求头

| 字段 | 必填 | 说明 |
|------|------|------|
| `Content-Type` | 是 | `application/json` |
| `Authorization` | 已登录接口需填 | `Bearer <access_token>` |

### 通用响应格式

```json
{
    "code": 0,
    "message": "success",
    "data": {}
}
```

### 通用错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 失效 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务未就绪 |

---

## 接口列表

---

### 1. 发送短信验证码

**POST** `/api/users/sms/send/`

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone` | string | 是 | 11 位手机号 |
| `purpose` | string | 否 | 用途：`login`（默认）/ `reset_password` / `bind_phone` |

#### 请求示例

```json
{
    "phone": "1*********0",
    "purpose": "login"
}
```

#### 成功响应 `200 OK`

```json
{
    "message": "验证码已发送"
}
```

#### 错误响应

```json
// 400 - 手机号格式不正确
{
    "phone": ["手机号格式不正确"]
}

// 429 - 请求过于频繁
{
    "error": "请求过于频繁，请稍后再试"
}

// 503 - 短信服务未配置
{
    "error": "短信服务未就绪，请检查 AccessKey 配置"
}
```

---

### 2. 手机号登录（登录 + 自动注册）

**POST** `/api/users/auth/phone-login/`

#### 功能说明

- 如果手机号不存在，**自动注册**并登录
- 如果手机号已存在，直接登录
- 返回用户基础信息（不含昵称/头像，由各应用 Profile 提供）
- 同时创建对应应用的 `UserAppProfile` 记录
- **新增特性**：当 `app_name=neighbor_hub` 时，自动创建基础 `NeighborHubProfile` 档案

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone` | string | 是 | 11 位手机号 |
| `code` | string | 是 | 4 位短信验证码 |
| `app_name` | string | 否 | 应用标识，默认 `neighbor_hub` |
| `invited_by` | UUID | 否 | 邀请人用户ID（可选） |

#### 请求示例

```json
{
    "phone": "1*********0",
    "code": "1234",
    "app_name": "neighbor_hub"
}
```

#### 邀请注册示例

**通过请求体传递邀请人**：
```json
{
    "phone": "1*********0",
    "code": "1234",
    "app_name": "neighbor_hub",
    "invited_by": "550e8400-e29b-41d4-a716-446655440000"
}
```

**通过URL参数传递邀请人**：
```
POST /api/users/auth/phone-login/?invited_by=550e8400-e29b-41d4-a716-446655440000
```

#### 成功响应

**新用户注册成功 `201 Created`**：

```json
{
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "phone": "138****8000",
        "is_new_user": true
    },
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 1800,
    "neighbor_hub_profile": {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "nickname": "138****8000",
        "is_new_profile": true,
        "is_profile_complete": false,
        "needs_completion": true
    }
}
```

*注：`neighbor_hub_profile` 字段仅在 `app_name=neighbor_hub` 时返回*

**老用户登录成功 `200 OK`**：

```json
{
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "phone": "138****8000",
        "is_new_user": false
    },
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 1800,
    "neighbor_hub_profile": {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "nickname": "张三",
        "is_new_profile": false,
        "is_profile_complete": true,
        "needs_completion": false
    }
}
```

*注：`neighbor_hub_profile` 字段仅在 `app_name=neighbor_hub` 时返回*

> **注意**：`nickname` 和 `avatar` 不在本接口返回，请调用对应应用的 Profile 接口获取。

#### 错误响应

```json
// 400 - 验证码错误
{
    "error": "验证码错误或已过期"
}

// 400 - 手机号格式错误
{
    "phone": ["手机号格式不正确"]
}
```

---

### 3. 登出

**POST** `/api/users/auth/logout/`

将 Refresh Token 加入黑名单。

#### 请求头

```
Authorization: Bearer <access_token>
```

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `refresh` | string | 是 | Refresh Token |

#### 请求示例

```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 成功响应 `200 OK`

```json
{
    "message": "登出成功"
}
```

---

### 4. 刷新 Token

**POST** `/api/users/auth/refresh/`

使用 Refresh Token 换取新的 Access Token。

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `refresh` | string | 是 | Refresh Token |

#### 请求示例

```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 成功响应 `200 OK`

```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

### 5. 获取当前用户信息

**GET** `/api/users/auth/profile/`

#### 请求头

```
Authorization: Bearer <access_token>
```

#### 成功响应 `200 OK`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 用户 UUID |
| `username` | string | 用户名 |
| `phone` | string | 脱敏手机号（138****8000） |
| `email` | string | 邮箱 |
| `date_joined` | datetime | 注册时间 |

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "user_1380080000",
    "phone": "138****8000",
    "email": "u***r@example.com",
    "date_joined": "2024-01-15T10:30:00Z"
}
```

---

## 数据模型

### User（用户基础模型）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `username` | string | 用户名（自动生成：`user_` + 手机号后8位） |
| `phone` | string | 手机号（唯一） |
| `email` | string | 邮箱（唯一，可为空） |
| `created_at` | datetime | 注册时间 |
| `updated_at` | datetime | 更新时间 |

### UserAppProfile（用户应用档案）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `user` | FK → User | 关联用户 |
| `app_name` | string | 应用标识 |
| `is_active` | bool | 是否激活（软删除标记） |
| `extra_data` | JSON | 扩展数据 |

### LoginRecord（登录记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `user` | FK → User | 关联用户 |
| `login_type` | string | 登录方式 |
| `ip_address` | string | IP 地址 |
| `app_name` | string | 登录应用 |
| `created_at` | datetime | 登录时间 |

### 新增响应字段说明

#### neighbor_hub_profile 字段（仅当 app_name=neighbor_hub 时返回）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | NeighborHubProfile主键 |
| `nickname` | string | 用户在业主黑板报应用中的昵称 |
| `is_new_profile` | boolean | 是否是新创建的档案 |
| `is_profile_complete` | boolean | 档案是否完整（是否有小区信息） |
| `needs_completion` | boolean | 是否需要进行档案完善 |

---

## 调用流程

```
用户进入 App
    │
    ▼
┌─────────────────────────────────┐
│  POST /api/users/sms/send/       │
│  输入手机号 → 发送验证码         │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  POST /api/users/auth/phone-login/ │
│  输入手机号 + 验证码             │
│  → 自动注册/登录 + 返回 Token    │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  保存 access / refresh Token     │
│  后续请求携带 Authorization      │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  调用各应用接口（携带 Token）    │
│  如 /api/neighbor_hub/...        │
└─────────────────────────────────┘
```

---

## 与 neighbor_hub 应用的分工

| 职责 | users 应用 | neighbor_hub 应用 |
|------|-----------|-------------------|
| 注册/登录 | ✅ 统一处理 | - |
| 验证码 | ✅ 发送/校验 | - |
| Token 颁发/刷新 | ✅ JWT 管理 | - |
| 昵称/头像 | - | ✅ NeighborHubProfile |
| 小区/房屋 | - | ✅ NeighborHubProfile |
| 角色（业委会/业主） | - | ✅ NeighborHubProfile |
| 应用访问标记 | ✅ UserAppProfile | - |

---

*文档更新时间：2024-07-21*
