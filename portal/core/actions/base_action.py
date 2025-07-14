from core.models import Action
from core.helpers import MessageObject, data_get, data_set
from django.core.cache import cache as redis

class BaseAction():
	def __init__(
		self,
		name: str,
		description: str,
		key: str = '',
		enabled: bool = True
	):
		self.model = data_get(
			model=Action,
			query_params={
				'name': name
			},
			key=f'action:{name}'
		)

		if len(self.model) == 0:
			self.model = data_set(
				model=Action,
				query_params={
					'name': name
				},
				model_params={
					'name': name,
					'description': description,
					'key': key,
					'enabled': enabled
				},
				key=f'action:{name}',
				create=True
			)
			
		self.name = name
		self.key = key
		self.description = description
		self.enabled = enabled


	def validate(self, msg: MessageObject) -> bool:
		"""
			Override this method to validate an input
		"""
		return False

	def generate(self, msg: MessageObject):
		"""
			Override this method for generation steps
		"""
		return