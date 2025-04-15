from django.urls import path
from .views import ImageConversionView , ImageConversionSearchView, TaskStatusCheckView

urlpatterns = [
    path('convert-image/', ImageConversionView.as_view(), name='convert-image'),
    path('search/', ImageConversionSearchView.as_view(), name='convert-image-search'),
    path('check_task_status/<str:task_id>/', TaskStatusCheckView.as_view(), name='task-status-check'),
]