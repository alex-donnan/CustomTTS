from django.urls import path
from . import views

urlpatterns = [
	path('', views.index),
	path('login/', views.login),
	path('login/confirm/', views.login_confirm)
]