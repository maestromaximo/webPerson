# Generated by Django 4.2.8 on 2024-01-22 02:56

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ChatModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=255, unique=True)),
                ('notes', models.TextField(blank=True)),
                ('model_name', models.CharField(default='gpt-3.5-turbo-0613', max_length=50)),
            ],
        ),
    ]