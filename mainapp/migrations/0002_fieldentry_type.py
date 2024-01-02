# Generated by Django 4.2.8 on 2024-01-02 21:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='fieldentry',
            name='type',
            field=models.CharField(choices=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal')], default='withdrawal', max_length=10),
        ),
    ]
