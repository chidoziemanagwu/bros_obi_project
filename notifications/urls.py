from django.urls import path
from . import views

urlpatterns = [
    path('', views.email_list, name='notifications_email_list'),
    path('<int:pk>/delete/', views.email_delete, name='notifications_email_delete'),
]