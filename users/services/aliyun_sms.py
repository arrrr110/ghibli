"""
阿里云短信认证服务 (dypnsapi) 封装
提供短信验证码发送和核验功能

SDK 文档: https://github.com/aliyun/alibabacloud-python-sdk/tree/master/dypnsapi-20170525
API 文档: https://help.aliyun.com/zh/pnvs/developer-reference/sms-authentication-server-integration

CLI 参考:
  发送: aliyun dypnsapi send-sms-verify-code --phone-number xxx --sign-name xxx --template-code xxx --template-param '{"code":"##code##"}'
  核验: aliyun dypnsapi verify-sms-code --phone-number xxx --verify-code xxx
"""
import json
import logging
from typing import Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


class AliyunSMSService:
    """阿里云短信认证服务封装"""

    def __init__(self):
        self.access_key_id = getattr(settings, 'ALIBABA_CLOUD_ACCESS_KEY_ID', '')
        self.access_key_secret = getattr(settings, 'ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')

        # 短信配置（固定值，从阿里云控制台获取）
        self.sign_name = getattr(settings, 'ALIYUN_SMS_SIGN_NAME', '恒创联众')
        self.template_code = getattr(settings, 'ALIYUN_SMS_TEMPLATE_CODE', '100001')

        # SDK 客户端
        self._client = None
        self._init_sdk()

    def _init_sdk(self):
        """初始化阿里云 SDK 客户端"""
        try:
            from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
            from alibabacloud_tea_openapi import models as open_api_models

            if self.access_key_id and self.access_key_secret:
                config = open_api_models.Config(
                    access_key_id=self.access_key_id,
                    access_key_secret=self.access_key_secret,
                    endpoint='dypnsapi.aliyuncs.com'
                )
                self._client = DypnsapiClient(config)
            else:
                logger.error('阿里云 AccessKey 未配置，短信服务不可用')
        except ImportError:
            logger.warning('alibabacloud-dypnsapi20170525 未安装，短信服务不可用')
        except Exception as e:
            logger.exception(f'初始化阿里云 SDK 失败: {e}')

    @property
    def is_ready(self) -> bool:
        """检查服务是否就绪"""
        return self._client is not None

    def send_verify_code(self, phone: str, code: str) -> Tuple[bool, str]:
        """
        发送短信验证码

        Args:
            phone: 手机号
            code: 要发送的验证码（4位数字）

        Returns:
            Tuple[success, message]
        """
        if not self.is_ready:
            return False, '短信服务未就绪（SDK 未初始化）'

        try:
            from alibabacloud_dypnsapi20170525 import models as dypnsapi_models

            request = dypnsapi_models.SendSmsVerifyCodeRequest(
                phone_number=phone,
                sign_name=self.sign_name,
                template_code=self.template_code,
                # TemplateParam: {"code":"##code##"}
                template_param='{"code":"##code##","min":"2"}',
            )

            response = self._client.send_sms_verify_code(request)
            logger.info(f'发送短信结果: phone={phone}, response_body={response.body}')

            if response.status_code == 200 and response.body.code == 'OK':
                request_id = response.body.request_id or ''
                logger.info(f'短信发送成功: phone={phone}, request_id={request_id}')
                return True, '验证码已发送'
            else:
                error_msg = response.body.message or '发送失败'
                logger.error(f'短信发送失败: {response.body.code} - {error_msg}')
                return False, error_msg

        except Exception as e:
            logger.exception(f'发送短信异常: {e}')
            return False, f'发送异常: {str(e)}'

    def verify_code(self, phone: str, code: str) -> Tuple[bool, str]:
        """
        核验短信验证码（使用 CheckSmsVerifyCode API，适合服务端/HTTP 调用）

        Args:
            phone: 手机号
            code: 用户输入的验证码

        Returns:
            Tuple[success, message]
        """
        if not self.is_ready:
            return False, '短信服务未就绪（SDK 未初始化）'

        try:
            from alibabacloud_dypnsapi20170525 import models as dypnsapi_models

            # 使用 CheckSmsVerifyCode（参数名为 VerifyCode），适合服务端
            request = dypnsapi_models.CheckSmsVerifyCodeRequest(
                phone_number=phone,
                verify_code=code,
            )

            response = self._client.check_sms_verify_code(request)
            logger.info(f'核验短信结果: phone={phone}, response_body={response.body}')

            if response.status_code == 200 and response.body.code == 'OK':
                logger.info(f'验证码核验成功: phone={phone}')
                return True, '验证成功'
            else:
                error_msg = response.body.message or '验证失败'
                logger.error(f'验证码核验失败: {response.body.code} - {error_msg}')
                return False, error_msg

        except Exception as e:
            logger.exception(f'核验短信异常: {e}')
            return False, f'验证异常: {str(e)}'


# 单例实例
_sms_service: AliyunSMSService = None


def get_sms_service() -> AliyunSMSService:
    """获取阿里云短信服务单例"""
    global _sms_service
    if _sms_service is None:
        _sms_service = AliyunSMSService()
    return _sms_service
