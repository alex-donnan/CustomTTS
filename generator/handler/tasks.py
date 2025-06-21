from celery import shared_task

@shared_task
def task1():
	print("Hello World")
	return