from django.db import models


class ImageConversionRecord(models.Model):
    """
    图片转换记录
    openid 保留用于兼容微信小程序，同时关联统一用户
    """
    # 关联统一用户（可选，兼容老数据）
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ghibli_images',
        verbose_name='关联用户',
    )
    # openid 保留用于微信小程序对接和查询
    openid = models.CharField(max_length=100, db_index=True, verbose_name='微信OpenID')
    task_id = models.CharField(max_length=255, unique=True, verbose_name='任务ID')
    status = models.CharField(max_length=20, default="PENDING", verbose_name='状态')
    prompt = models.TextField(verbose_name='提示词')
    url = models.URLField(verbose_name='图片URL')
    record_time = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')

    class Meta:
        db_table = 'image_conversion_records'
        verbose_name = '图片转换记录'
        verbose_name_plural = verbose_name
        ordering = ['-record_time']

    def __str__(self):
        return f'{self.openid} - {self.task_id[:8]}'


class TaskResult(models.Model):
    task_id = models.CharField(max_length=255, unique=True, verbose_name='任务ID')
    status = models.CharField(max_length=20, default="PENDING", verbose_name='状态')
    result = models.TextField(blank=True, null=True, verbose_name='结果')

    class Meta:
        db_table = 'task_results'
        verbose_name = '任务结果'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.task_id
