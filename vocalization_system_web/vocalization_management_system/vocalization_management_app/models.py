from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('1', 'Admin'),
        ('2', 'Staff'),
    )
    user_type = models.CharField(max_length=1, choices=USER_TYPE_CHOICES, default='2')
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, default="User")

    def __str__(self):
        return self.email

# Admin Profile Model
class AdminProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

# Staff Profile Model
class StaffProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    department = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
