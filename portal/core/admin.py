from django.contrib import admin
from .models import User, UserSetting, UserModeratorRef

admin.site.register(User)
admin.site.register(UserModeratorRef)
admin.site.register(UserSetting)
