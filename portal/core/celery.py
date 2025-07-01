import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_routes = {
	'core.tasks.core_tasks.*': {'queue': 'core_queue'},
	'core.tasks.generator_tasks.*': {'queue': 'generator_queue'}
}
app.autodiscover_tasks()