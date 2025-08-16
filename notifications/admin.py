from django.contrib import admin
from .models import NotificationEmail

@admin.register(NotificationEmail)
class NotificationEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'added_at')
    search_fields = ('email',)