from django.db import models

# Users (streamer or mod)
class User(models.Model):
	user = models.CharField(
		verbose_name='Twitch User ID',
		unique=True
	)
	login = models.CharField(verbose_name='User Name')
	display_name = models.CharField(verbose_name='User Display Name')
	type = models.CharField(verbose_name='User type')
	broadcaster_type = models.CharField(verbose_name='Broadcaster Type')
	channel_description = models.CharField(verbose_name='Channel Description')
	profile_image_url = models.CharField(verbose_name='Profile Image URL')
	email = models.CharField(verbose_name='Email Address', default=None, blank=True, null=True)
	enabled = models.BooleanField(verbose_name='User Enabled', default=True)
	token = models.CharField(verbose_name='User Auth Token', default='')
	refresh = models.CharField(verbose_name='User Auth Refresh', default='')

	def __str__(self):
		return f'{self.user} : {self.login} / {self.display_name}'

# Moderator XRef
class UserModeratorRef(models.Model):
	user = models.ForeignKey(
		User,
		to_field='user',
		on_delete=models.CASCADE,
		related_name='channel_owner'
	)
	moderator = models.CharField(verbose_name='Moderator User ID')

	class Meta:
		unique_together = ('user', 'moderator')

	def __str__(self):
		return f'Broadcaster {self.user}: Moderated by {self.moderator}'

# Actions
class Action(models.Model):
	name = models.CharField(
		verbose_name='Action Name',
		unique=True
	)
	key = models.CharField(verbose_name='Action Key')
	description = models.CharField(verbose_name='Action Description')
	enabled = models.BooleanField(verbose_name='Action Globally Enabled')

# Triggers
class Trigger(models.Model):
	name = models.CharField(
		verbose_name='Trigger Name',
		unique=True
	)
	description = models.CharField(verbose_name='Trigger Description')
	event = models.CharField(
		verbose_name='Event Type',
		unique=True
	)
	enabled = models.BooleanField(verbose_name='Trigger Globally Enabled')

# Settings
class UserSetting(models.Model):
	# General Fields
	user = models.ForeignKey(
		User,
		to_field='user',
		on_delete=models.CASCADE,
		verbose_name='Channel Settings'
	)
	media_location = models.CharField(
		verbose_name='Media file path for assets',
		max_length=50
	)
	action_type = models.ForeignKey(
		Action,
		to_field='name',
		on_delete=models.CASCADE,
		verbose_name='Action Type'
	)
	trigger_type = models.ForeignKey(
		Trigger,
		to_field='event',
		on_delete=models.CASCADE,
		verbose_name='Trigger Event Type',
	)
	enabled = models.BooleanField(
		verbose_name='Action is enabled',
		default=False
	)
	paused = models.BooleanField(
		verbose_name='Action is paused',
		default=False
	)
	cost = models.IntegerField(
		verbose_name='Trigger Cost',
		default=0
	)

	class Meta:
		unique_together = ('user', 'action_type', 'trigger_type')

	def __str__(self):
		return f'Setting for {self.user}: {self.action_type} on {self.trigger_type} : {"Enabled" if self.enabled else "Disabled"} : Costs {self.cost}'
