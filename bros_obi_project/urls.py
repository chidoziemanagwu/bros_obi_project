from django.contrib import admin
from django.urls import path, include
from staff.views import landing_login  # or from core.views if you put it there

urlpatterns = [
    path('', landing_login, name='landing_login'),
    path('admin/', admin.site.urls),
    path('products/', include('products.urls')),
    path('staff/', include('staff.urls')),
    path('sales/', include('sales.urls')),
    path('notifications/', include('notifications.urls')),
]