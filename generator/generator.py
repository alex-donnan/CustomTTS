from celery import Celery

app = Celery('generator')
app.config_from_object('config')
app.conf.imports = ('core.tasks')
app.conf.task_routes = {
	'core.tasks.task1': {'queue': 'generator_queue'},
	'core.tasks.task2': {'queue': 'listener_queue'}
}