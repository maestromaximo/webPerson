# Generated by Django 4.2.1 on 2024-05-04 03:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0017_chatsession_remove_gptinstance_tools_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LessonEmbedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('vector', models.JSONField()),
                ('lesson', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='embedding', to='education.lesson')),
            ],
        ),
    ]