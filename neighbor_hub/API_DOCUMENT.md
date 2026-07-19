# 用户认证 API 接口文档

> **Base URL**: `http://your-domain.com/api/users/`  
> **认证方式**: JWT (Bearer Token)  
> **最后更新时间**: 2026-07-19

---

## 认证说明

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

## 公开接口（无需登录）

> 验证码相关接口无需认证，其他接口需携带 JWT Token

---

### 1. 发送短信验证码

**POST** `/api/users/sms/send/`

请求体：
```json
{
  "phone": "13800138000",
  "purpose": "login"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✅ | 手机号（11位数字） |
| purpose | string | 否 | 用途：`login` / `register` / `reset_password` / `bind_phone`，默认 `login` |

响应：
```json
{
  "message": "验证码已发送"
}
```

**限流**：同一手机号 60 秒内只能发送一次

---

### 2. 手机号统一登录（登录 + 自动注册）

**POST** `/api/users/auth/phone-login/`

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
| code | string | ✅ | 6位短信验证码 |
| app_name | string | 否 | 应用标识，默认 `neighbor_hub` |

**功能说明**：
- 如果手机号**不存在**，自动创建新用户并登录（返回 HTTP 201）
- 如果手机号**已存在**，直接登录（返回 HTTP 200）
- 无需区分"注册"和"登录"，一步到位

响应（老用户登录 - HTTP 200）：
```json
{
  "user": {
    "id": "uuid",
    "nickname": "用户昵称",
    "phone": "138****8000",
    "avatar": "头像URL",
    "is_new_user": false
  },
  "access": "eyJ...",
  "refresh": "eyJ...",
  "expires_in": 1800
}
```

响应（新用户自动注册 - HTTP 201）：
```json
{
  "user": {
    "id": "uuid",
    "nickname": "用户5678",
    "phone": "138****8000",
    "avatar": "",
    "is_new_user": true
  },
  "access": "eyJ...",
  "refresh": "eyJ...",
  "expires_in": 1800
}
```

**通过 `is_new_user` 字段可判断是否为新注册用户**，前端可用于引导新用户完善资料

---

### 3. 刷新 Token

**POST** `/api/users/auth/refresh/`

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

### 4. 登出

**POST** `/api/users/auth/logout/`

需要认证：✅

请求体：
```json
{
  "refresh": "eyJ..."
}
```

> 将 Refresh Token 加入黑名单使其失效

响应：
```json
{
  "message": "登出成功"
}
```

---

### 5. 获取当前用户信息

**GET** `/api/users/auth/profile/`

需要认证：✅

响应：
```json
{
  "id": "uuid",
  "username": "user_13800138",
  "nickname": "用户昵称",
  "phone": "138****8000",
  "avatar": "头像URL",
  "date_joined": "2026-07-19T10:00:00Z",
  "app_profile": {
    "app_name": "neighbor_hub",
    "extra_data": {}
  }
}
```

---

## 接口路由总览

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/users/sms/send/` | ❌ | 发送短信验证码 |
| POST | `/api/users/auth/phone-login/` | ❌ | 手机号统一登录（登录+自动注册） |
| POST | `/api/users/auth/logout/` | ✅ | 登出 |
| POST | `/api/users/auth/refresh/` | ❌ | 刷新 JWT Token |
| GET  | `/api/users/auth/profile/` | ✅ | 获取当前用户信息 |

---

## 统一响应格式

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
| 200 | 成功（老用户登录） |
| 201 | 创建成功（新用户自动注册） |
| 400 | 请求参数错误 |
| 401 | 未认证（Token 无效或缺失） |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 短信服务未就绪 |

---

## 前端对接示例

### 登录流程

```
1. POST /api/users/sms/send/       → 发送验证码
2. POST /api/users/auth/phone-login/ → 登录（自动注册）
   检查 response.user.is_new_user:
     - true: 新用户，可引导完善昵称、头像
     - false: 老用户，直接进入主页
3. 存储 access_token 和 refresh_token
4. 后续请求携带 Authorization: Bearer <access_token>
5. 收到 401 时，POST /api/users/auth/refresh/ 刷新 Token
```

### Axios 拦截器配置

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
          const { data } = await axios.post('/api/users/auth/refresh/', { refresh })
          localStorage.setItem('access_token', data.access)
          localStorage.setItem('refresh_token', data.refresh)
          error.config.headers.Authorization = `Bearer ${data.access}`
          return axios(error.config)
        } catch {
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

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.1.0 | 2026-07-19 | 合并 register 和 phone-login 为统一登录接口；移除微信登录；统一 API 路径为 /api/users/ |
| v1.0.0 | 2026-07-19 | 初始版本 |
