"""Модуль с роутами."""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

app_name = "parse"

urlpatterns = [
    path('', views.add_link, name='add_link', ),
    path('results/', views.results, name='results'),
    path('success/', views.success, name='success'),
] + static(settings.MEDIA_URL, document_root='media')
