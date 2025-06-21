from celery import Celery

app = Celery('generator')
app.config_from_object('config')
app.conf.imports = ('handler.tasks')