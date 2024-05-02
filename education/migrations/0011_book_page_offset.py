# Generated by Django 4.2.1 on 2024-04-19 03:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0010_alter_tool_associated_problem'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='page_offset',
            field=models.IntegerField(default=0, help_text='The page number of the first page in the book from where the page count starts, for example page 1 could start counting on the physical page 7, after the preface.'),
        ),
    ]