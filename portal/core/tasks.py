from celery import shared_task

@shared_task
def task1():
	print('Sending a task to generator')
	return

@shared_task
def task2():
	print('Sending a task to listener')
	return