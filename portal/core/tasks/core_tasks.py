from core.models import User, UserModeratorRef, UserSetting
from core.celery import app
from celery.signals import worker_ready

@app.task
def create_user(username: str):
	# Call twitch API for user
	return 'butt'

	# Create the user
	# Create the task for user settings and moderators

@app.task
def create_user_setting(user: User):
	return 'booty'

@app.task
def create_moderator_ref(user: User):
	return 'bootimus'