
from django.contrib import admin
from .models import ContactMessage
from django.core.mail import send_mail

@admin.register(ContactMessage)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'replied', 'created_at']

    def save_model(self, request, obj, form, change):
        # If reply is added and not already sent
        if obj.reply and not obj.replied:
            send_mail(
                subject="Reply to your query",
                message=obj.reply,
                from_email="your_email@gmail.com",  # your email
                                                   #enter password
                recipient_list=[obj.email],
                fail_silently=False,
            )
            obj.replied = True

        super().save_model(request, obj, form, change)
