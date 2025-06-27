from django.contrib import admin
from .models import User, UserSettings, UserModeratorRef

admin.site.register(User)
admin.site.register(UserModeratorRef)
admin.site.register(UserSettings)
