from django.http import HttpResponse
from django.shortcuts import render

def index(request):
	print('responding hello')
	return HttpResponse("Hello World")