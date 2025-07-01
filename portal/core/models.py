from django.db import models

# Users (streamer or mod)
class User(models.Model):
	user_id = models.CharField(verbose_name='Twitch User ID')
	login = models.CharField(verbose_name='User Name')
	display_name = models.CharField(verbose_name='User Display Name')
	type = models.CharField(verbose_name='User type')
	broadcaster_type = models.CharField(verbose_name='Broadcaster Type')
	channel_description = models.CharField(verbose_name='Channel Description')
	profile_image_url = models.CharField(verbose_name='Profile Image URL')
	email = models.CharField(verbose_name='Email Address')

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