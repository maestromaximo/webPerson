# Generated by Django 4.2.8 on 2024-03-29 21:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0003_book_slug_class_slug_lesson_slug_problem_title'),
    ]

    operations = [
        migrations.CreateModel(
            name='Prompt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('prompt', models.TextField()),
                ('description', models.TextField(blank=True, null=True)),
                ('category', models.CharField(blank=True, max_length=100, null=True)),
                ('active', models.BooleanField(default=True)),
            ],
        ),
    ]
