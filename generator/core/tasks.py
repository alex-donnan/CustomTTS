from celery import shared_task
from time import sleep

@shared_task
def task1(input=None):
	return "Hello World"

@shared_task
def task2(input=None):
	return