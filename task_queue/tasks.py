# tasks.py
import time
import requests
import logging
from celery import shared_task
from .models import TaskResult, ImageConversionRecord
import re
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def call_third_party_api(self):
    task_id = self.request.id.lower()
    print('aorui:', task_id)
    try:
        # 创建任务记录，初始状态为 PENDING
        task_result = TaskResult.objects.create(task_id=task_id)
        print('aorui task_result:', task_result)
        # 模拟调用第三方接口，等待 120 秒
        time.sleep(120)
        # 调用第三方接口
        url = "http://127.0.0.1:8000/search/?format=json&openid=aorui123"  # 替换为实际的第三方接口 URL
        response = requests.get(url)
        if response.status_code == 200:
            # 百度的 API 不会直接返回 JSON 格式数据，这里需要根据实际情况调整
            result = response.text
            # 更新任务状态为 SUCCESS，并保存结果
            task_result.status = 'SUCCESS'
            task_result.result = result
            task_result.save()
            return result
        else:
            # 更新任务状态为 FAILURE
            task_result.status = 'FAILURE'
            task_result.result = f"Request failed with status code {response.status_code}"
            task_result.save()
            return None
    except Exception as e:
        logger.error(f"Task {task_id} failed with error: {str(e)}", exc_info=True)
        try:
            task_result = TaskResult.objects.get(task_id=task_id)
            task_result.status = 'FAILURE'
            task_result.result = str(e)
            task_result.save()
        except TaskResult.DoesNotExist:
            logger.error(f"Task {task_id} record not found in database when trying to save failure status.")
        return None
    

@shared_task(bind=True)
def create_image(self, openid, prompt, base64_image):
    task_id = self.request.id

    # 目标 URL
    url = os.getenv('url')
    # APIkey
    APIkey = os.getenv('APIkey')
    # 设置请求头，包含 APIkey
    headers = {
        "Authorization": APIkey,
        "Content-Type": "application/json"
    }
    
    try:
        # 创建任务记录，初始状态为 PENDING
        task_result = ImageConversionRecord.objects.create(
                    task_id=task_id,
                    openid=openid,
                    prompt=prompt
                )
        # 构建请求参数
        data = {
            "model": "gpt-4o-image-vip",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        }

        # 发送 POST 请求
        response = requests.post(url, json=data, headers=headers)
        # 处理响应
        if response.status_code == 200:
            response_data = response.json()
            # 定位到 https://filesystem.site/cdn/…… 的 url 链接
            url_pattern = r'https://filesystem\.site/cdn/\d{8}/[a-zA-Z0-9]+\.png'
            match = re.search(url_pattern, str(response_data))
            if match:
                # 更新任务状态为 SUCCESS，并保存结果
                task_result.status = 'SUCCESS'
                url_link = match.group(0)
                task_result.url = url_link
                task_result.save()

                return url_link
            else:
                task_result.status = 'FAILURE'
                task_result.save()
                return "未找到符合条件的 URL 链接"
        else:
            task_result.status = 'FAILURE'
            task_result.save()
            return None
    except Exception as e:
        logger.error(f"Task {task_id} failed with error: {str(e)}", exc_info=True)
        try:
            task_result = ImageConversionRecord.objects.get(task_id=task_id)
            task_result.status = 'FAILURE'
            task_result.save()
        except TaskResult.DoesNotExist:
            logger.error(f"Task {task_id} record not found in database when trying to save failure status.")
        return None