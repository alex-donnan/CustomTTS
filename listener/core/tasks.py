from celery import shared_task
from time import sleep

@shared_task
def task1(input=None):
	return

@shared_task
def task2(input=None):
	sleep(10)
	print("Hello World")
	return