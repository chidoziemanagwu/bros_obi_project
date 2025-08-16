from django.contrib import admin
from .models import StaffProfile

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'pin')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')