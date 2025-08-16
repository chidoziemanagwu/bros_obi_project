from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'quantity', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('name',)