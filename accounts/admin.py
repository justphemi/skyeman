"""Accounts admin — keep Django's default User admin but tidy it up slightly."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Use Django's default User admin, no extra customisation needed
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
