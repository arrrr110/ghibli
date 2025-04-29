import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImageConversionSerializer
from .models import ImageConversionRecord , TaskResult
import re
from django.http import JsonResponse
from .tasks import create_image
import logging

logger = logging.getLogger(__name__)

class ImageConversionView(APIView):
    def post(self, request):
        try:
            serializer = ImageConversionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            openid = serializer.validated_data['openid']
            prompt = serializer.validated_data['prompt']
            base64_image = serializer.validated_data['base64_image']

            # 调用 celery 任务
            task = create_image.delay(openid, prompt, base64_image)

            return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            # 处理其他未知异常
            logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ImageConversionSearchView(APIView):
    def get(self, request):
        openid = request.query_params.get('openid')
        if not openid:
            return Response({"error": "缺少 openid 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            records = ImageConversionRecord.objects.filter(openid=openid)
            data = []
            for record in records:
                data.append({
                    # "openid": record.openid,
                    "task_id": record.task_id,
                    "status": record.status,
                    # "prompt": record.prompt,
                    "url": record.url,
                    "record_time": record.record_time
                })
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class TaskStatusCheckView(APIView):
    def get(self, request, task_id):
        try:
            task_result = ImageConversionRecord.objects.get(task_id=task_id)
            data = {
                'status': task_result.status,
                'url': task_result.url
            }
            return Response(data, status=status.HTTP_200_OK)
        except TaskResult.DoesNotExist:
            logger.error(f"An unexpected error occurred: {TaskResult}", exc_info=True)
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)