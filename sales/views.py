from django.shortcuts import render
from .models import Sale

def sales_history(request):
    sales = Sale.objects.all()
    return render(request, 'sales/history.html', {'sales': sales})