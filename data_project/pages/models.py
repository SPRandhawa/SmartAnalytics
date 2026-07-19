
from django.db import models

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()

    reply = models.TextField(blank=True, null=True)  # ADMIN WILL WRITE HERE

    created_at = models.DateTimeField(auto_now_add=True)
    replied = models.BooleanField(default=False)

    def __str__(self):
        return self.name