from django.contrib import admin
from .models import FoodItem, Meal


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'purchased_date', 'expiration_date', 'weight', 'quantity_per_package', 'calories', 'fat', 'protein', 'carbohydrates', 'sugars', 'sodium')
    list_filter = ('purchased_date', 'expiration_date', 'weight', 'quantity_per_package', 'calories', 'fat', 'protein', 'carbohydrates', 'sugars', 'sodium')
    search_fields = ('name',)
    date_hierarchy = 'purchased_date'
    ordering = ('-purchased_date',)
    exclude = ('purchased_date', 'nutritional_values',)  # Exclude auto-populated and specific fields

    fieldsets = (
        (None, {
            'fields': ('name', 'image', 'expiration_date', 'weight', 'quantity_per_package')
        }),
        ('Nutritional Information', {
            'fields': ('calories', 'fat', 'protein', 'carbohydrates', 'sugars', 'sodium')
        }),
    )

@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'total_calories', 'total_fat', 'total_protein', 'total_carbohydrates', 'total_sugars', 'total_sodium')
    list_filter = ('date', 'total_calories', 'total_fat', 'total_protein', 'total_carbohydrates', 'total_sugars', 'total_sodium')
    search_fields = ('name',)
    date_hierarchy = 'date'
    ordering = ('-date',)

    fieldsets = (
        (None, {
            'fields': ('name', 'date', 'recipe')
        }),
        ('Nutritional Totals', {
            'fields': ('total_calories', 'total_fat', 'total_protein', 'total_carbohydrates', 'total_sugars', 'total_sodium')
        }),
        ('Associated Food Items', {
            'fields': ('food_items',),
            'description': 'Select food items that make up this meal.'
        }),
    )

    filter_horizontal = ('food_items',)  # For easier selection of multiple food items