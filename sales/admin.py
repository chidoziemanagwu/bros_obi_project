from django.contrib import admin
from .models import Sale

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'staff', 'quantity', 'price_at_sale', 'timestamp')
    list_filter = ('timestamp', 'staff')
    search_fields = ('product__name', 'staff__username')