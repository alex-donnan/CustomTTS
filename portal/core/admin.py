from django.contrib import admin
from .models import User, \
	UserSetting, \
	UserModeratorRef, \
	Action, \
	Trigger


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	list_display = ('user', 'login', 'enabled')

	@admin.display(description='ID')
	def user(self, obj):
		return obj.user

	@admin.display(description='Twitch Login')
	def login(self, obj):
		return obj.login

	@admin.display(description='Enabled')
	def enabled(self, obj):
		return obj.enabled

@admin.register(UserModeratorRef)
class UserModeratorRefAdmin(admin.ModelAdmin):
	list_display = ('broadcaster', 'moderator')

	@admin.display(description='Broadcaster')
	def broadcaster(self, obj):
		return obj.user

	@admin.display(description='Moderator')
	def moderator(self, obj):
		return obj.moderator

@admin.register(UserSetting)
class UserSettingAdmin(admin.ModelAdmin):
	list_display = ('user', 'action', 'trigger', 'enabled')

	@admin.display(description='Broadcaster')
	def user(self, obj):
		return obj.user
	
	@admin.display(description='Action')
	def action(self, obj):
			return obj.action_type

	@admin.display(description='Trigger')
	def trigger(self, obj):
		return obj.trigger_type

	@admin.display(description='Enabled')
	def enabled(self, obj):
		return obj.enabled

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
	list_display = ('action', 'enabled')

	@admin.display(description='Action')
	def action(self, obj):
		return obj.name

	@admin.display(description='Enabled')
	def enabled(self, obj):
		return obj.enabled

admin.site.register(Trigger)
