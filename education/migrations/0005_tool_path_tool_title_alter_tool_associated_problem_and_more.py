# Generated by Django 4.2.8 on 2024-03-29 21:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0004_prompt'),
    ]

    operations = [
        migrations.AddField(
            model_name='tool',
            name='path',
            field=models.FilePathField(blank=True, help_text='Path to the tool', null=True),
        ),
        migrations.AddField(
            model_name='tool',
            name='title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='tool',
            name='associated_problem',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tools', to='education.problem'),
        ),
        migrations.AlterField(
            model_name='tool',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]