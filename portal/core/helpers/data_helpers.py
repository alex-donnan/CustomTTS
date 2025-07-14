from django.core.cache import cache as redis
from django.db import models

"""
	Standard methods for retrieving or updating DB and cache

	Default ttl within the cache is 12 hours. This could be reduced if need be.
"""

# Get data from the cache > DB
# Will return a list of valid responses (allowing both redis * queries and db multiple returns)
# List is transformed to model instances
def data_get(
	model: type[models.Model],
	query_params: dict,
	key: str | None = '',
	ttl: int | None = 43200
) -> list[type[models.Model]]:
	data = None

	if key != '':
		data = redis.get(key)

	if data is None:
		data = list(model.objects.filter(**query_params))
		if len(data) > 0 and not '*' in key:
			redis.set(key, data, ttl)
		else:
			print('Unable to generate cache for element. Please do so manually.')
	elif type(data) is dict:
		data = list(map(lambda el: model(**el), data))

	return data

# Sets a single model instance's values, DB > cache
# Does not have to be comprehensive, can select individual fields
def data_set(
	model: type[models.Model],
	query_params: dict,
	model_params: dict,
	key: str,
	create: bool = False,
	ttl: int | None = 43200
) -> type[models.Model] | None:
	data = None
	try:
		data = model.objects.get(**query_params)
		for key, value in model_params.items():
			setattr(data, key, value)
		data.save()
	except model.DoesNotExist:
		print('Could not find matching instance of model.')
		
		if create:
			try:
				print('Create enabled, creating model.')
				data = model.objects.create(**model_params)
			except Exception as ex:
				print(f'Failed to create model: {ex}')
		else:
			print('Create not enabled, aborting.')
			return None
	finally:
		if data is not None:
			redis.set(key, [data], ttl)
		return data

# Probably need delete
# for both redis and database