from django.db import models

# Create your models here.

class FieldEntry(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]

    date = models.DateField()
    time = models.TimeField()
    message = models.TextField()
    money = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
        default='withdrawal',
    )
    read_status = models.BooleanField(default=False)