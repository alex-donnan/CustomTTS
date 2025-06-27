from django.db import models

# Users (streamer or mod)
class User(models.Model):
	user_id = models.CharField(verbose_name='Twitch User ID')
	user_name = models.CharField(
		verbose_name='Twitch User/Channel Name',
		max_length=50
	)
	profile_name = models.CharField(
		verbose_name='Twitch User Display Name',
		max_length=50
	)
	profile_url = models.CharField(
		verbose_name='Twitch Profile URL',
		max_length=200
	)
	channel_id = models.CharField(verbose_name='Twitch Channel ID')
	channel_description = models.CharField(
		verbose_name='Channel description',
		max_length=300
	)
	last_live = models.DateField(verbose_name='Last Date Channel was Live')
	last_authentication = models.DateField(verbose_name='Last Date Authenticated')

	def __str__(self):
		return f'{self.user_id}'

# Moderator XRef
class UserModeratorRef(models.Model):
	user = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name='channel_owner'
	)
	moderator = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name = 'channel_moderator'
	)

	class Meta:
		unique_together = ('user', 'moderator')

	def __str__(self):
		return f'Broadcaster {self.user.user_id}: Moderated by {self.moderator.user_id}'

# Settings
class UserSetting(models.Model):
	# Message triggers
	TRIGGER_TYPES = [
		('message', 'Chat Message'),
		('cheer', 'Bits Used'),
		('sub', 'Subscription, Renewal, or Gift')
	]

	# General Fields
	user = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		verbose_name='Channel Settings'
	)
	media_location = models.CharField(
		verbose_name='Media file path for assets',
		max_length=50
	)
	tts_enabled = models.BooleanField(verbose_name='TTS enabled')
	tts_trigger = models.CharField(
		verbose_name='TTS message trigger',
		choices=TRIGGER_TYPES
	)
	tts_cost = models.IntegerField(verbose_name='TTS relevant trigger cost')
	tts_model_enabled = models.BooleanField(verbose_name='TTS speaker model enabled')
	sound_enabled = models.BooleanField(verbose_name='Sound Bite enabled')
	sound_trigger = models.CharField(
		verbose_name='Sound Bite message trigger',
		choices=TRIGGER_TYPES
	)
	sound_cost = models.IntegerField(verbose_name='Sound Bite relevant trigger cost')
	lute_enabled = models.BooleanField(verbose_name='LuteBoi enabled')
	lute_trigger = models.CharField(
		verbose_name='LuteBoi message trigger',
		choices=TRIGGER_TYPES
	)
	lute_cost = models.IntegerField(verbose_name='LuteBoi relevant trigger cost')