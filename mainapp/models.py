from django.db import models

# Create your models here.

class FieldEntry(models.Model):
    date = models.DateField()
    time = models.TimeField()
    message = models.TextField()
    money = models.DecimalField(max_digits=10, decimal_places=2)
    read_status = models.BooleanField(default=False)