from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImageConversionSerializer
from .models import ImageConversionRecord, TaskResult
from .tasks import create_image
import logging
from django.shortcuts import render, HttpResponse
from django.utils import timezone
from datetime import timedelta, time
from django.contrib.auth.decorators import login_required, user_passes_test


logger = logging.getLogger(__name__)


class ImageConversionView(APIView):
    def post(self, request):
        try:
            serializer = ImageConversionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            openid = serializer.validated_data["openid"]
            prompt = serializer.validated_data["prompt"]
            base64_image = serializer.validated_data["base64_image"]

            # 调用 celery 任务
            task = create_image.delay(openid, prompt, base64_image)

            return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            # 处理其他未知异常
            logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ImageConversionSearchView(APIView):
    def get(self, request):
        openid = request.query_params.get("openid")
        if not openid:
            return Response(
                {"error": "缺少 openid 参数"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            records = ImageConversionRecord.objects.filter(openid=openid)
            data = []
            for record in records:
                data.append(
                    {
                        # "openid": record.openid,
                        "task_id": record.task_id,
                        "status": record.status,
                        # "prompt": record.prompt,
                        "url": record.url,
                        "record_time": record.record_time,
                    }
                )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TaskStatusCheckView(APIView):
    def get(self, request, task_id):
        try:
            # test
            # task = debug_task.delay()
            # print(f"debug_task_id:{task.id}")
            task_result = ImageConversionRecord.objects.get(task_id=task_id)
            data = {"status": task_result.status, "url": task_result.url}
            return Response(data, status=status.HTTP_200_OK)
        except TaskResult.DoesNotExist:
            logger.error(f"An unexpected error occurred: {TaskResult}", exc_info=True)
            return Response(
                {"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )


# 检查用户是否是管理员
def is_admin(user):
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    now = timezone.now()
    # 初始化过去10天的日期数组和计数器
    daily_counts = []
    for i in range(10):
        # 计算当天的开始和结束时间（时区感知）
        day = now - timedelta(days=i)
        day_start = timezone.make_aware(timezone.datetime.combine(day.date(), time.min))
        day_end = timezone.make_aware(timezone.datetime.combine(day.date(), time.max))

        # 统计当天SUCCESS和FAILURE的记录数
        success_count = ImageConversionRecord.objects.filter(
            status="SUCCESS", record_time__range=(day_start, day_end)
        ).count()

        failure_count = ImageConversionRecord.objects.filter(
            status="FAILURE", record_time__range=(day_start, day_end)
        ).count()

        daily_counts.append(
            {
                "date": day.date(),
                "success_count": success_count,
                "failure_count": failure_count,
            }
        )
    daily_counts.reverse()
    # 获取最近5个任务（无论状态）
    recent_tasks = ImageConversionRecord.objects.order_by("-record_time")[:5]

    # 准备任务列表数据
    task_list = []
    for task in recent_tasks:
        task_list.append(
            {
                "id": task.pk,
                "task_id": task.task_id,
                "status": task.status,
                "record_time": task.record_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status_label": get_status_label(task.status),
            }
        )

    print(task_list)
    return render(
        request,
        "dashboard.html",
        {"daily_counts": daily_counts, "recent_tasks": task_list},
    )


def get_status_label(status):
    """根据状态返回对应的标签样式"""
    status_mapping = {
        "SUCCESS": {"class": "bg-green-100 text-green-800", "icon": "fa-check-circle"},
        "FAILURE": {"class": "bg-red-100 text-red-800", "icon": "fa-times-circle"},
        "PENDING": {"class": "bg-yellow-100 text-yellow-800", "icon": "fa-clock-o"},
    }
    return status_mapping.get(
        status, {"class": "bg-gray-100 text-gray-800", "icon": "fa-question-circle"}
    )
