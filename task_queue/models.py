from django.db import models


class ImageConversionRecord(models.Model):
    openid = models.CharField(max_length=100)
    task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, default="PENDING")
    prompt = models.TextField()
    url = models.URLField()
    record_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.openid


class TaskResult(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, default="PENDING")
    result = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.task_id
