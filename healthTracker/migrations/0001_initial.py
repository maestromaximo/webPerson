# Generated by Django 4.2.8 on 2024-01-03 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FoodItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('image', models.ImageField(blank=True, null=True, upload_to='food_images/')),
                ('nutritional_values', models.TextField()),
                ('purchased_date', models.DateField(auto_now_add=True)),
                ('expiration_date', models.DateField(blank=True, null=True)),
                ('weight', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('quantity_per_package', models.IntegerField(blank=True, null=True)),
                ('calories', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('fat', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('protein', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('carbohydrates', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('sugars', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('sodium', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
            ],
        ),
    ]
