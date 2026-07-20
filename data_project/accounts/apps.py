from django.apps import AppConfig
   import os

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals

        # ✅ SAFE PLACE TO CREATE SUPERUSER
     
        if os.environ.get("CREATE_SUPERUSER") == "True":
            from django.contrib.auth.models import User

            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser(
                    username="admin",
                    email="admin@gmail.com",
                    password="admin123"
                )
