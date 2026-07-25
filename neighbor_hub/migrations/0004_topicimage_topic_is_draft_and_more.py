# Generated for neighbor_hub image upload feature

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('neighbor_hub', '0003_alter_topicsubscription_options_and_more'),
    ]

    operations = [
        # Topic: title 改为 blank=True（草稿允许空标题）
        migrations.AlterField(
            model_name='topic',
            name='title',
            field=models.CharField(blank=True, max_length=100, verbose_name='标题'),
        ),
        # Topic: content 改为 blank=True（草稿允许空内容）
        migrations.AlterField(
            model_name='topic',
            name='content',
            field=models.TextField(blank=True, verbose_name='内容'),
        ),
        # Topic: 移除 image_url 字段
        migrations.RemoveField(
            model_name='topic',
            name='image_url',
        ),
        # Topic: 新增 is_draft 字段
        migrations.AddField(
            model_name='topic',
            name='is_draft',
            field=models.BooleanField(default=False, verbose_name='草稿'),
        ),
        # 新建 TopicImage 模型
        migrations.CreateModel(
            name='TopicImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('image_url', models.URLField(verbose_name='图片访问URL')),
                ('oss_key', models.CharField(max_length=255, verbose_name='OSS对象key')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='排序')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('topic', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='images',
                    to='neighbor_hub.topic',
                )),
            ],
            options={
                'verbose_name': '话题图片',
                'verbose_name_plural': '话题图片',
                'db_table': 'neighbor_hub_topic_images',
                'ordering': ['sort_order', 'created_at'],
            },
        ),
    ]
