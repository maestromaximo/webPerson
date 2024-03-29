# Generated by Django 5.0 on 2024-02-14 06:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gptInterface', '0005_alter_chatsession_title'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(blank=True, help_text='Username', max_length=255, null=True, unique=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_pictures/')),
                ('name', models.CharField(blank=True, help_text='Full Name', max_length=255, null=True)),
                ('email', models.EmailField(blank=True, help_text='Email Address', max_length=254, null=True, unique=True)),
                ('phone', models.IntegerField(help_text='Phone Number', null=True)),
                ('access_level', models.CharField(choices=[('basic', 'Basic'), ('premium', 'Premium'), ('advanced', 'Advanced')], default='basic', help_text='Access Level', max_length=50)),
                ('usage_costs', models.DecimalField(decimal_places=2, default=0, help_text='Usage Costs', max_digits=10)),
                ('api_rate_hourly', models.IntegerField(default=20, help_text='API Rate Hourly')),
                ('password', models.CharField(blank=True, help_text='Password', max_length=255, null=True)),
                ('bio', models.TextField(blank=True, help_text='A short bio about the User [Optional]', null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
