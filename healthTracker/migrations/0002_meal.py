# Generated by Django 4.2.8 on 2024-01-04 03:19

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('healthTracker', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Meal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, default='No Name', max_length=255)),
                ('date', models.DateField(default=datetime.date.today)),
                ('recipe', models.TextField(blank=True, null=True)),
                ('total_calories', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_fat', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_protein', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_carbohydrates', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_sugars', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_sodium', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('food_items', models.ManyToManyField(to='healthTracker.fooditem')),
            ],
        ),
    ]
