from django.db import models
from datetime import date

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

class Meal(models.Model):
    name = models.CharField(max_length=255, blank=True, default='No Name')
    date = models.DateField(default=date.today)
    food_items = models.ManyToManyField(FoodItem)
    recipe = models.TextField(blank=True, null=True)
    total_calories = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_fat = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_protein = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_carbohydrates = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_sugars = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_sodium = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return self.name or f"Meal on {self.date}"

    def calculate_totals(self):
        """Calculate total nutritional values from the associated food items."""
        self.total_calories = sum(item.calories for item in self.food_items.all())
        self.total_fat = sum(item.fat for item in self.food_items.all())
        self.total_protein = sum(item.protein for item in self.food_items.all())
        self.total_carbohydrates = sum(item.carbohydrates for item in self.food_items.all())
        self.total_sugars = sum(item.sugars for item in self.food_items.all())
        self.total_sodium = sum(item.sodium for item in self.food_items.all())
        self.save()

