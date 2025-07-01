from celery import shared_task

# Shared tasks with generator only need to be named here
# The actual generator container will hold their full definitions

@shared_task
def task1():
	print('Sending a task to generator')
	return

@shared_task
def task2():
	print('Sending a task to listener')
	return