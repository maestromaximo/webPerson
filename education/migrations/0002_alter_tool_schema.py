# Generated by Django 4.2.8 on 2024-03-24 03:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tool',
            name='schema',
            field=models.JSONField(),
        ),
    ]
