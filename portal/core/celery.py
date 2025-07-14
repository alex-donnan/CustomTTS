import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_routes = {
	'core.tasks.*': {'queue': 'generator_queue'}
}
app.autodiscover_tasks()