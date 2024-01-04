from django.contrib import admin
from .models import FoodItem


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