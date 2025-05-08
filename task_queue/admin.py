from django.contrib import admin
from .models import ImageConversionRecord, TaskResult
from django.utils.html import format_html

admin.site.site_header = "吉卜力生图AI"
admin.site.site_title = "吉卜力生图"


class ImageConversionRecordAdmin(admin.ModelAdmin):
    list_display = ("openid", "status", "show_image_mini")
    ordering = ("-record_time",)
    readonly_fields = ("show_image",)

    def show_image(self, obj):
        return format_html('<img src="{}" width="200" />', obj.url)

    def show_image_mini(self, obj):
        return format_html('<img src="{}" width="20" />', obj.url)

    show_image.short_description = "图片预览"


admin.site.register(ImageConversionRecord, ImageConversionRecordAdmin)


# test
@admin.register(TaskResult)
class AuthorAdmin(admin.ModelAdmin):
    # list show
    list_display = ["task_id", "status", "result", "view_result_id"]
    # detail show / in one line
    fields = (("task_id", "status"), "result", "view_result_id")
    # bottom show on bottom
    actions_on_bottom = True
    # date_hierarchy = 'pub_date'
    empty_value_display = "-empty-"

    readonly_fields = ("view_result_id",)

    def view_result_id(self, obj):
        return obj.result

    view_result_id.empty_value_display = "???"
    view_result_id.short_description = "一个函数，接收模型实例作为参数"


# admin.site.register(TaskResult, AuthorAdmin)
