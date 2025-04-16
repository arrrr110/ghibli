from django.contrib import admin
from .models import ImageConversionRecord, TaskResult

class ImageConversionRecordAdmin(admin.ModelAdmin):
    # 定义在admin列表页面显示的字段
    list_display = ('openid', 'task_id', 'status')
    # 定义默认排序方式，'-record_time'表示按record_time字段降序排列
    ordering = ('-record_time',)

# 注册模型和对应的ModelAdmin类
admin.site.register(ImageConversionRecord, ImageConversionRecordAdmin)
# admin.site.register(TaskResult)