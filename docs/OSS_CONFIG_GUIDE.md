# 阿里云 OSS 配置指南

> 本文档记录了在 Django 项目中接入阿里云 OSS（对象存储）的完整配置过程，可直接复用于后续项目。
>
> 参考代码：`neighbor_hub/services/oss_client.py`
> 官方文档：https://help.aliyun.com/zh/oss/developer-reference/python-sdk-v1/

---

## 目录

1. [概览](#1-概览)
2. [前置准备](#2-前置准备)
3. [创建 Bucket](#3-创建-bucket)
4. [RAM 权限配置（关键）](#4-ram-权限配置关键)
5. [安装依赖](#5-安装依赖)
6. [环境变量配置](#6-环境变量配置)
7. [Django Settings 配置](#7-django-settings-配置)
8. [代码封装](#8-代码封装)
9. [CNAME 自定义域名（可选）](#9-cname-自定义域名可选)
10. [Endpoint 选择策略](#10-endpoint-选择策略)
11. [常见问题排查](#11-常见问题排查)
12. [安全检查清单](#12-安全检查清单)

---

## 1. 概览

本项目使用阿里云 OSS 存储用户上传的图片（话题图片、用户头像），通过 `oss2`（Python SDK V1）实现上传与删除。

**核心架构：**

```
用户 → Django API → oss2 SDK → OSS Bucket → CNAME 域名 → 浏览器访问图片
```

**涉及的技术栈：**

| 组件 | 说明 |
|------|------|
| `oss2` | 阿里云 OSS Python SDK V1，`pip install oss2` |
| `Pillow` | 图片格式校验（读取文件头防伪造扩展名） |
| `python-dotenv` | 从 `.env` 文件加载环境变量 |

---

## 2. 前置准备

1. **注册阿里云账号**，完成实名认证。
2. **开通 OSS 服务**：访问 https://www.aliyun.com/product/oss ，点击开通。
   - OSS 按量付费，有免费额度（新用户可领存储包）。
3. **确认主账号 AccessKey 位置**：https://ram.console.aliyun.com/manage/ak
   > ⚠️ **安全提醒**：**不要使用主账号 AccessKey** 直接写在代码里！主账号 AK 泄露=全部资产沦陷。必须创建 RAM 子账号（见第 4 节）。

---

## 3. 创建 Bucket

进入 OSS 控制台：https://oss.console.aliyun.com/

### 关键配置项

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| **Bucket 名称** | `your-project-name` | 全局唯一，创建后不可改。小写字母+数字+短横线 |
| **区域** | 华东2（上海）`cn-shanghai` | 选离用户最近或与 ECS 同区域（内网免流量费） |
| **存储类型** | 标准存储 | 适用于频繁访问的图片 |
| **读写权限** | **公共读** | 图片需通过 URL 直接访问。⚠️ 切勿选"公共读写" |
| **服务端加密** | 无（或 KMS） | 公共读 Bucket 加密会影响直接访问，按需配置 |
| **实时日志查询** | 开启 | 方便排查访问异常 |
| **版本控制** | 关闭（图片场景不需要） | 开启会产生多版本存储费用 |
| **定时备份** | 按需 | 重要数据建议开启 |

### 读写权限说明

| 权限 | 含 | 适用场景 |
|------|------|------|
| 私有 | 所有操作需 AK 鉴权 | 敏感文件（合同、证件） |
| **公共读** | 写需鉴权，读匿名 | ✅ **本项目**：用户上传的图片 |
| 公共读写 | 读写均匿名 | ❌ **绝对禁止**，会被恶意写入 |

> **为什么选公共读？**
> 上传走后端（有 AK 鉴权），访问图片走前端 URL（匿名读取）。这样前端直接用 `<img src="https://...">` 展示，无需临时签名。

---

## 4. RAM 权限配置（关键）

> 🔴 **这是整个配置中最关键的安全环节。** 用 RAM 子账号替代主账号操作，遵循**最小权限原则**。

### 4.1 创建 RAM 子账号

1. 进入 RAM 控制台：https://ram.console.aliyun.com/users
2. **用户** → **创建用户**
   - 登录名：`oss-uploader`（按用途命名）
   - 访问方式：勾选 **OpenAPI 调用访问**（✅），**不勾选**控制台登录（无需控制台权限）
3. 创建后**立即保存** `AccessKey ID` 和 `AccessKey Secret`
   > ⚠️ Secret 只在创建时显示一次，关掉页面就看不到了！

### 4.2 创建自定义权限策略

RAM → 权限策略 → 创建权限策略 → 脚本编辑

**最小权限策略（推荐）：**

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:GetObject",
        "oss:DeleteObject",
        "oss:ListParts",
        "oss:AbortMultipartUpload",
        "oss:ListObjects"
      ],
      "Resource": [
        "acs:oss:*:*:your-bucket-name",
        "acs:oss:*:*:your-bucket-name/*"
      ]
    }
  ]
}
```

> **替换 `your-bucket-name` 为你的 Bucket 名称。**
>
> Resource 中两行缺一不可：
> - 第一行 `acs:oss:*:*:bucket` — 针对 Bucket 本身的操作（如 List）
> - 第二行 `acs:oss:*:*:bucket/*` — 针对 Bucket 内对象的操作（如 Put/Get/Delete）

**各 Action 说明：**

| Action | 用途 | 本项目是否需要 |
|--------|------|------|
| `oss:PutObject` | 上传/覆盖对象 | ✅ |
| `oss:GetObject` | 读取对象 | ✅（可选，公共读 Bucket 匿名也能读） |
| `oss:DeleteObject` | 删除对象 | ✅ |
| `oss:ListObjects` | 列举 Bucket 内对象 | ✅（调试用） |
| `oss:ListParts` | 列举分片上传的分片 | ✅（大文件上传） |
| `oss:AbortMultipartUpload` | 取消分片上传 | ✅（清理残留分片） |

> 💡 **不要用 `oss:*` 通配**，一旦 AK 泄露，攻击者可删掉整个 Bucket。

### 4.3 给子账号授权

RAM → 用户 → 找到 `oss-uploader` → **权限管理** → 新增授权 → 选择上一步创建的策略。

### 4.4 验证权限

用子账号 AK 在本地快速验证：

```python
import oss2

auth = oss2.Auth('子账号AK_ID', '子账号AK_SECRET')
bucket = oss2.Bucket(auth, 'https://oss-cn-shanghai.aliyuncs.com', 'your-bucket-name')

# 测试上传
result = bucket.put_object('test.txt', b'hello oss')
print(f'上传状态: {result.status}')  # 200 = 成功

# 测试删除
bucket.delete_object('test.txt')
print('删除成功')
```

如果报 `AccessDenied`，说明策略 Resource/Action 配置有误，回到 4.2 检查。

---

## 5. 安装依赖

```bash
pip install oss2==2.19.1
pip install Pillow==11.2.1
```

> **版本说明**：
> - `oss2` 2.x 是 Python SDK V1（稳定）。阿里云另有 V2 SDK（`oss2` 包名不变，API 有差异），本项目用 V1。
> - `Pillow` 用于上传时读取图片文件头验证真实格式，防止用户把 `.txt` 改名成 `.jpg` 上传。

`requirements.txt` 中添加：

```
oss2==2.19.1
Pillow==11.2.1
```

---

## 6. 环境变量配置

在项目根目录 `.env` 文件中添加（**切勿提交到 Git**，确保 `.gitignore` 包含 `.env`）：

```ini
# ============================================
# 阿里云 OSS 配置（图片存储）
# ============================================
# AccessKey（使用 RAM 子账号的 AK，不要用主账号！）
OSS_ACCESS_KEY_ID = "你的子账号AK_ID"
OSS_SECRET_ACCESS_KEY = "你的子账号AK_SECRET"

# Bucket 名称（在 OSS 控制台创建的）
OSS_BUCKET_NAME = "your-bucket-name"

# Endpoint（取决于 Bucket 所在区域）
# 开发环境用外网端点
OSS_ENDPOINT = "https://oss-cn-shanghai.aliyuncs.com"
# 生产环境（ECS 部署）用内网端点（同区域免流量费）
OSS_ENDPOINT_INTERNAL = "https://oss-cn-shanghai-internal.aliyuncs.com"

# 自定义域名（CNAME 绑定后填入；不填则用 OSS 默认域名）
OSS_CUSTOM_DOMAIN = "https://your-bucket-name.oss-cn-shanghai.aliyuncs.com"
```

### Endpoint 格式说明

```
外网：https://oss-cn-{区域}.aliyuncs.com
内网：https://oss-cn-{区域}-internal.aliyuncs.com
```

常见区域：

| 区域 | 外网 Endpoint |
|------|------|
| 华东2（上海） | `https://oss-cn-shanghai.aliyuncs.com` |
| 华北1（青岛） | `https://oss-cn-qingdao.aliyuncs.com` |
| 华北2（北京） | `https://oss-cn-beijing.aliyuncs.com` |
| 华南1（深圳） | `https://oss-cn-shenzhen.aliyuncs.com` |

---

## 7. Django Settings 配置

在 `settings.py` 中添加（通过 `python-dotenv` 从 `.env` 读取）：

```python
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 阿里云 OSS 配置（图片存储）
# ============================================
# 文档: https://help.aliyun.com/zh/oss/developer-reference/python-sdk-v1/
# SDK: pip install oss2

# AccessKey（从环境变量读取，使用 RAM 子账号）
OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
OSS_SECRET_ACCESS_KEY = os.getenv('OSS_SECRET_ACCESS_KEY', '')

# Bucket 名称
OSS_BUCKET_NAME = os.getenv('OSS_BUCKET_NAME', '')

# Endpoint：开发用外网，生产用内网（同区域 ECS 访问 OSS 免流量费）
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'https://oss-cn-shanghai.aliyuncs.com')
OSS_ENDPOINT_INTERNAL = os.getenv('OSS_ENDPOINT_INTERNAL', 'https://oss-cn-shanghai-internal.aliyuncs.com')
# 根据 DEBUG 自动切换：开发用外网，生产用内网
OSS_ACTIVE_ENDPOINT = OSS_ENDPOINT if DEBUG else OSS_ENDPOINT_INTERNAL

# CNAME 自定义域名（图片访问 URL 前缀）
OSS_CUSTOM_DOMAIN = os.getenv('OSS_CUSTOM_DOMAIN', '')

# 图片上传约束
MAX_IMAGE_SIZE = 500 * 1024  # 500KB
MAX_IMAGES_PER_TOPIC = 9
ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp', 'gif']
```

**关键点：`OSS_ACTIVE_ENDPOINT` 自动切换逻辑**

```python
OSS_ACTIVE_ENDPOINT = OSS_ENDPOINT if DEBUG else OSS_ENDPOINT_INTERNAL
```

- `DEBUG=True`（开发）→ 外网 Endpoint，本地电脑能访问
- `DEBUG=False`（生产）→ 内网 Endpoint，ECS 通过内网访问 OSS，**免公网流量费**

> ⚠️ 内网 Endpoint 只有在与 OSS **同区域**的 ECS 上才能访问，本地开发用内网会连接超时。

---

## 8. 代码封装

完整代码见 `neighbor_hub/services/oss_client.py`，核心结构如下：

### 8.1 初始化 Bucket 实例

```python
import oss2
from django.conf import settings

def _get_bucket():
    """获取 OSS2 Bucket 实例（每次调用时读取最新配置）"""
    auth = oss2.Auth(
        settings.OSS_ACCESS_KEY_ID,
        settings.OSS_SECRET_ACCESS_KEY,
    )
    bucket = oss2.Bucket(
        auth,
        settings.OSS_ACTIVE_ENDPOINT,
        settings.OSS_BUCKET_NAME,
    )
    return bucket
```

### 8.2 上传图片

```python
def upload_topic_image(topic_id: str, file_obj) -> dict:
    ext = _get_file_extension(file_obj.name)
    filename = f"{uuid.uuid4().hex}.{ext}"
    oss_key = f"topics/{topic_id}/{filename}"

    bucket = _get_bucket()
    file_obj.seek(0)
    data = file_obj.read()

    # 设置 Content-Type + Content-Disposition 让浏览器在线显示（而非下载）
    content_type = _MIME_TYPES.get(ext, 'application/octet-stream')
    result = bucket.put_object(oss_key, data, headers={
        'Content-Type': content_type,
        'Content-Disposition': 'inline',
    })
    if result.status != 200:
        raise Exception(f'OSS 上传失败，HTTP {result.status}')

    return {
        'oss_key': oss_key,
        'image_url': _build_image_url(oss_key),
    }
```

**关键设计点：**

1. **文件名用 UUID**：`uuid.uuid4().hex`，避免同名覆盖，也避免中文文件名编码问题。
2. **目录结构按业务划分**：`topics/{topic_id}/{filename}`、`avatars/{user_id}/{filename}`，方便批量管理和清理。
3. **设置 `Content-Disposition: inline`**：让浏览器直接在线显示图片，不会触发下载。
4. **设置 `Content-Type`**：正确的 MIME 类型（如 `image/jpeg`），否则浏览器可能当二进制下载。
5. **同时返回 `oss_key` 和 `image_url`**：`oss_key` 存数据库用于删除，`image_url` 给前端展示。

### 8.3 删除对象

```python
def delete_oss_object(oss_key: str) -> bool:
    try:
        bucket = _get_bucket()
        bucket.delete_object(oss_key)
        return True
    except Exception as e:
        logger.error(f'删除 OSS 对象失败: {oss_key} - {e}')
        return False
```

### 8.4 通过 URL 删除（头像更新场景）

```python
def delete_oss_object_by_url(url: str) -> bool:
    """从图片 URL 中提取 oss_key 并删除（用于只存了 URL 没存 key 的场景）"""
    if not url:
        return False
    domain = settings.OSS_CUSTOM_DOMAIN.rstrip('/')
    if url.startswith(domain):
        oss_key = url[len(domain) + 1:]  # 去掉域名前缀 + '/'
        return delete_oss_object(oss_key)
    logger.warning(f'URL 不属于当前 OSS 域名，跳过删除: {url}')
    return False
```

### 8.5 图片格式校验（防伪造）

```python
from PIL import Image

def validate_image(file_obj) -> tuple:
    # 1. 大小校验
    file_size = file_obj.size
    if file_size > settings.MAX_IMAGE_SIZE:
        return '', f'图片大小不能超过 {settings.MAX_IMAGE_SIZE // 1024}KB'

    # 2. 扩展名校验
    ext = _get_file_extension(file_obj.name)
    if ext not in _ALLOWED_FORMATS:
        return '', f'不支持的图片格式：.{ext}'

    # 3. Pillow 读取文件头验证真实格式（防止 .txt 改名为 .jpg）
    file_obj.seek(0)
    img = Image.open(file_obj)
    if img.format != _ALLOWED_FORMATS[ext]:
        return '', f'文件内容与扩展名不匹配'
    file_obj.seek(0)  # 校验后重置指针，供后续读取

    return ext, None
```

### 8.6 配合 Django 信号自动清理 OSS

在 Model 中用 `pre_delete` 信号，确保各种删除场景（单条删、批量删、级联删）都能清理 OSS：

```python
from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=TopicImage)
def _topic_image_pre_delete(sender, instance, **kwargs):
    """删除 TopicImage 时同步删除 OSS 上的文件"""
    from .services.oss_client import delete_oss_object
    if instance.oss_key:
        delete_oss_object(instance.oss_key)
```

> **为什么用 `pre_delete` 而不是重写 `delete()`？**
> `delete()` 只在单条 `.delete()` 调用时触发，`QuerySet.delete()`（批量删）和 CASCADE 级联删除不会调用。`pre_delete` 信号在所有场景都会触发。

### 8.7 MIME 类型映射表

```python
_MIME_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'gif': 'image/gif',
}
```

---

## 9. CNAME 自定义域名（可选）

绑定自己的域名（如 `https://oss.your-domain.com`）代替 OSS 默认域名，更专业且便于后续接 CDN。

### 配置步骤

1. **域名备案**：域名需在阿里云完成 ICP 备案。
2. **OSS 控制台** → Bucket → **传输管理** → **域名管理** → 绑定域名。
3. **DNS 解析**：在域名 DNS 中添加 CNAME 记录：
   - 记录类型：`CNAME`
   - 主机记录：`oss`（或你想要的子域名前缀）
   - 记录值：`your-bucket-name.oss-cn-shanghai.aliyuncs.com`
4. **HTTPS**（可选但推荐）：在 OSS 控制台上传 SSL 证书，开启 HTTPS 访问。
5. **更新环境变量**：
   ```ini
   OSS_CUSTOM_DOMAIN = "https://oss.your-domain.com"
   ```

> ⚠️ CNAME 生效需要时间（DNS 传播），配好后用 `nslookup oss.your-domain.com` 验证是否解析到 OSS。

---

## 10. Endpoint 选择策略

| 场景 | 用哪个 Endpoint | 原因 |
|------|------|------|
| 本地开发 | 外网 `oss-cn-xxx.aliyuncs.com` | 本地电脑只能走公网 |
| ECS 生产（与 OSS 同区域） | 内网 `oss-cn-xxx-internal.aliyuncs.com` | **免公网流量费**，速度快 |
| ECS 生产（与 OSS 跨区域） | 外网 | 内网仅同区域可用 |
| 函数计算（同区域） | 内网 | 免流量费 |

**本项目自动切换逻辑：**

```python
OSS_ACTIVE_ENDPOINT = OSS_ENDPOINT if DEBUG else OSS_ENDPOINT_INTERNAL
```

> 💡 生产部署时确保 `DEBUG=False`，否则 ECS 走外网会产生公网流量费。

---

## 11. 常见问题排查

### 11.1 上传报 `AccessDenied`

**原因**：RAM 权限策略配置错误。

**排查**：
1. 检查策略中 `Resource` 是否包含 `bucket/*`（对象级操作需要）。
2. 检查 `Action` 是否包含 `oss:PutObject`。
3. 确认 AK 是子账号的，且已授权该策略。

### 11.2 上传成功但图片访问是下载

**原因**：没设置 `Content-Disposition` 或设成了 `attachment`。

**解决**：上传时设置 headers：
```python
bucket.put_object(oss_key, data, headers={
    'Content-Type': 'image/jpeg',
    'Content-Disposition': 'inline',  # ✅ inline = 在线显示
})
```

### 11.3 内网 Endpoint 连接超时

**原因**：内网 Endpoint 只能在同区域 ECS 上访问，本地或跨区域不行。

**解决**：开发环境确保用外网 Endpoint（`DEBUG=True` 自动切外网）。

### 11.4 删除报 `NoSuchKey`

**原因**：要删除的对象不存在（可能已被手动删除）。

**处理**：OSS 删除不存在的对象默认不报错（幂等），如果报错说明权限或 Bucket 名有问题。

### 11.5 中文文件名乱码

**原因**：OSS 对象 key 建议用英文+数字。

**解决**：本项目用 `uuid.uuid4().hex` 生成文件名，天然避免此问题。

### 11.6 `ModuleNotFoundError: No module named 'oss2'`

**解决**：`pip install oss2`，并确认 `requirements.txt` 中已包含。

---

## 12. 安全检查清单

- [ ] **不使用主账号 AK**，已创建 RAM 子账号并使用其 AK
- [ ] RAM 子账号遵循最小权限原则（只授权指定 Bucket 的 Put/Get/Delete）
- [ ] `.env` 文件已加入 `.gitignore`，不会提交到 Git
- [ ] Bucket 读写权限设为"公共读"（而非"公共读写"）
- [ ] 生产环境 `DEBUG=False`，使用内网 Endpoint
- [ ] 上传文件大小限制（本项目 500KB）
- [ ] 上传格式校验（Pillow 读取文件头，防伪造扩展名）
- [ ] AccessKey Secret 不出现在代码、日志、错误信息中
- [ ] CNAME 域名已配 HTTPS（如已绑定自定义域名）

---

## 附：完整配置速查

```ini
# .env
OSS_ACCESS_KEY_ID = "子账号AK_ID"
OSS_SECRET_ACCESS_KEY = "子账号AK_SECRET"
OSS_BUCKET_NAME = "your-bucket-name"
OSS_ENDPOINT = "https://oss-cn-shanghai.aliyuncs.com"
OSS_ENDPOINT_INTERNAL = "https://oss-cn-shanghai-internal.aliyuncs.com"
OSS_CUSTOM_DOMAIN = "https://your-bucket-name.oss-cn-shanghai.aliyuncs.com"
```

```python
# settings.py
OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
OSS_SECRET_ACCESS_KEY = os.getenv('OSS_SECRET_ACCESS_KEY', '')
OSS_BUCKET_NAME = os.getenv('OSS_BUCKET_NAME', '')
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'https://oss-cn-shanghai.aliyuncs.com')
OSS_ENDPOINT_INTERNAL = os.getenv('OSS_ENDPOINT_INTERNAL', 'https://oss-cn-shanghai-internal.aliyuncs.com')
OSS_ACTIVE_ENDPOINT = OSS_ENDPOINT if DEBUG else OSS_ENDPOINT_INTERNAL
OSS_CUSTOM_DOMAIN = os.getenv('OSS_CUSTOM_DOMAIN', '')
MAX_IMAGE_SIZE = 500 * 1024
MAX_IMAGES_PER_TOPIC = 9
ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp', 'gif']
```

```bash
# 依赖
pip install oss2==2.19.1 Pillow==11.2.1
```

---

*文档维护：配置变更后同步更新此文件。*
