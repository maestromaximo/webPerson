# Generated by Django 4.2.8 on 2024-01-22 01:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0010_budgetcategory_bar_color'),
    ]

    operations = [
        migrations.AlterField(
            model_name='budgetcategory',
            name='name',
            field=models.CharField(choices=[('transportation', 'Transportation'), ('food', 'Food'), ('entertainment', 'Entertainment'), ('takeout', 'Takeout'), ('supplies', 'Supplies'), ('overspent', 'Overspent')], max_length=50, unique=True),
        ),
    ]
