from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/profile/', views.manager_profile, name='manager_profile'),
    path('register/', views.manager_register, name='manager_register'),
    path('logout/', views.logout_view, name='logout'),  # Add this

    path('products/', views.products_list, name='products_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/toggle/', views.product_toggle_status, name='product_toggle_status'),
    
    path('manage/', views.staff_list, name='staff_list'),
    path('manage/add/', views.staff_create, name='staff_create'),
    path('manage/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('manage/<int:pk>/toggle/', views.staff_toggle_active, name='staff_toggle_active'),


    path('manager/profile/', views.manager_profile, name='manager_profile'),
    path('manager/profile/edit/', views.manager_profile_edit, name='manager_profile_edit'),
    path('manager/profile/password/', views.manager_password_change, name='manager_password_change'),


    path('history/', views.sales_history, name='sales_history'),
    path('sell/', views.sale_create, name='sale_create'),
    path('price-list/', views.price_list, name='price_list'),
    
    path('staff-password-change/', views.staff_password_change, name='staff_password_change'),


    path('staff/history/', views.staff_sales_history, name='staff_sales_history'),      # staff only (their own)
    path('manager/history/', views.sales_history, name='sales_history'),

]