from django.db import models
from django.contrib.auth.models import User
from products.models import Product

class Sale(models.Model):
    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product} sold by {self.staff} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-timestamp']