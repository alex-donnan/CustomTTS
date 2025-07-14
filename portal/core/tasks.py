from celery import shared_task
from core.actions import BaseAction
from core.helpers import MessageObject

"""
	Shared generator task passes the specific action's generate function
"""
@shared_task
def generate(action: BaseAction, msg: MessageObject):
	return action.generate(msg)