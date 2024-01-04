from django.db import models

class FoodItem(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='food_images/', blank=True, null=True)
    nutritional_values = models.TextField()  # Store nutritional values as a string
    purchased_date = models.DateField(auto_now_add=True)
    expiration_date = models.DateField(blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    quantity_per_package = models.IntegerField(blank=True, null=True)

    # Additional fields for individual nutritional entries
    calories = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    fat = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    protein = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    carbohydrates = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    sugars = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    sodium = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    # You can add more fields as per your nutritional data requirements

    def __str__(self):
        return self.name
    

