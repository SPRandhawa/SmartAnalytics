from django.db.models.signals import post_save, post_migrate
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile
import os


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_migrate)
def create_superuser(sender, **kwargs):
    # ✅ RUN ONLY FOR YOUR APP
    if sender.name != "accounts":
        return

    if os.environ.get("CREATE_SUPERUSER") == "True":
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@gmail.com",
                password="admin123"
            )
