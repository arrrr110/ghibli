"""
阿里云 OSS 客户端封装

提供图片上传、删除功能。
使用 oss2 SDK (Python SDK V1)。

文档: https://help.aliyun.com/zh/oss/developer-reference/python-sdk-v1/
"""

import io
import logging
import uuid

import oss2
from PIL import Image
from django.conf import settings

logger = logging.getLogger(__name__)

# 允许的图片格式 → PIL format 映射
# key 是文件扩展名（小写），value 是 Pillow Image.format
_ALLOWED_FORMATS = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
    'gif': 'GIF',
}

# 扩展名 → MIME 类型映射（上传时设置 Content-Type，让浏览器在线显示而非下载）
_MIME_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'gif': 'image/gif',
}


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


def _get_file_extension(filename: str) -> str:
    """从文件名获取小写扩展名（不含点）"""
    parts = filename.rsplit('.', 1)
    if len(parts) < 2:
        return ''
    return parts[1].lower()


def _build_image_url(oss_key: str) -> str:
    """拼接图片可访问 URL（使用 CNAME 自定义域名）"""
    domain = settings.OSS_CUSTOM_DOMAIN.rstrip('/')
    return f"{domain}/{oss_key}"


def validate_image(file_obj) -> tuple:
    """
    校验上传的图片文件

    校验项:
    - 文件大小 ≤ MAX_IMAGE_SIZE (500KB)
    - 格式为 jpg/jpeg/png/webp/gif（通过 Pillow 读取文件头验证，不仅看扩展名）

    Args:
        file_obj: Django InMemoryUploadedFile 或 TemporaryUploadedFile

    Returns:
        tuple: (ext: str, error: str|None)
            ext  — 小写的文件扩展名（校验通过时）
            error — 错误信息（校验失败时），None 表示通过

    Raises:
        无异常抛出，错误通过返回值传递
    """
    # 1. 大小校验
    file_size = file_obj.size if hasattr(file_obj, 'size') else len(file_obj.read())
    if file_size > settings.MAX_IMAGE_SIZE:
        return '', f'图片大小不能超过 {settings.MAX_IMAGE_SIZE // 1024}KB（当前 {file_size // 1024}KB）'

    # 2. 扩展名校验
    ext = _get_file_extension(file_obj.name)
    if ext not in _ALLOWED_FORMATS:
        allowed = ', '.join(settings.ALLOWED_IMAGE_FORMATS)
        return '', f'不支持的图片格式：.{ext}，仅允许 {allowed}'

    # 3. Pillow 验证文件头（防止伪造扩展名）
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)
        img_format = img.format  # 'JPEG', 'PNG', 'WEBP', 'GIF'
        # 验证 PIL 识别的格式与扩展名一致
        expected_format = _ALLOWED_FORMATS[ext]
        if img_format != expected_format:
            # gif 动图的格式也是 GIF，正常匹配
            return '', f'文件内容与扩展名不匹配（文件实际格式: {img_format}）'
        file_obj.seek(0)
    except Exception as e:
        file_obj.seek(0)
        logger.warning(f'图片格式校验失败: {e}')
        return '', '无法识别的图片文件，请上传有效的图片'

    return ext, None


def upload_topic_image(topic_id: str, file_obj) -> dict:
    """
    上传话题图片到 OSS

    Args:
        topic_id: 话题 UUID（字符串）
        file_obj: 上传的文件对象

    Returns:
        dict: {
            'oss_key': str,      — OSS 中的对象 key
            'image_url': str,    — 可访问的完整 URL
        }

    Raises:
        Exception: OSS 上传失败时抛出
    """
    ext = _get_file_extension(file_obj.name)
    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex}.{ext}"
    oss_key = f"topics/{topic_id}/{filename}"

    bucket = _get_bucket()

    # 读取文件内容
    file_obj.seek(0)
    data = file_obj.read()

    # 上传到 OSS（设置 Content-Type + Content-Disposition 让浏览器在线显示图片）
    content_type = _MIME_TYPES.get(ext, 'application/octet-stream')
    result = bucket.put_object(oss_key, data, headers={
        'Content-Type': content_type,
        'Content-Disposition': 'inline',
    })
    if result.status != 200:
        raise Exception(f'OSS 上传失败，HTTP {result.status}')

    logger.info(f'图片上传成功: {oss_key} ({len(data)} bytes)')

    return {
        'oss_key': oss_key,
        'image_url': _build_image_url(oss_key),
    }


def delete_oss_object(oss_key: str) -> bool:
    """
    删除 OSS 上的单个对象

    Args:
        oss_key: OSS 对象 key

    Returns:
        bool: 是否删除成功
    """
    try:
        bucket = _get_bucket()
        bucket.delete_object(oss_key)
        logger.info(f'OSS 对象已删除: {oss_key}')
        return True
    except Exception as e:
        logger.error(f'删除 OSS 对象失败: {oss_key} - {e}')
        return False
