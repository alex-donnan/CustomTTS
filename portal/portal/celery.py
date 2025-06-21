import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')

app = Celery('portal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_routes = {
	'handler.tasks.task1': {'queue': 'generator_queue'},
	'handler.tasks.task2': {'queue': 'listener_queue'}
}
app.autodiscover_tasks()