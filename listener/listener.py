from celery import Celery

app = Celery('listener')
app.config_from_object('config')
app.conf.imports = ('handler.tasks')