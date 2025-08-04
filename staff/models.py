from django.db import models
from django.contrib.auth.models import User

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('deleted', 'Deleted'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    pin = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username