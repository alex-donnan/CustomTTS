from core.helpers import data_get, data_set
from core.models import User
from django.apps import apps
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
import asyncio

def index(request):
	return HttpResponse("Hello World")

def login(request):
	global twitch_handler
	twitch_handler = apps.get_app_config('core').twitch_handler

	username = request.GET.get('username')
	if username is None:
		return HttpResponse('Missing parameter username', status=400)

	return HttpResponseRedirect(f'{twitch_handler.auth.return_auth_url()}?username={username}')

def login_confirm(request):
	state = request.GET.get('state').split('?')[0]
	username = request.GET.get('state').split('=')[1]
	code = request.GET.get('code')

	if state != twitch_handler.auth.state:
		return HttpResponse('Bad State, unauthorized.', status=401)
	if code is None:
		return HttpResponse('Missing code', status=400)

	try:
		token, refresh = asyncio.run(twitch_handler.auth.authenticate(user_token=code))
		user = data_get(
			model=User,
			query_params={
				'login': username
			}
		)

		if len(user) == 0:
			raise Exception('Failed to find user by username')

		user = data_set(
			model=User,
			query_params={
				'user': user[0].user
			},
			model_params={
				'token': token,
				'refresh': refresh
			},
			key=f'user:{user[0].user}:detail'
		)

		asyncio.run(twitch_handler.subscribe_user(user))
	except Exception as ex:
		return HttpResponse(f'Failed to generate auth tokens: {ex}', 400)

	return HttpResponse('Auth completed succesfully')