from django.contrib.auth.models import User
from django.db import models


__all__ = ["Profile"]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return self.user.username