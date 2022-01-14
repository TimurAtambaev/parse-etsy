from django.urls import path
from . import views

app_name = "parse"

urlpatterns = [
    path('', views.add_link, name='add_link', ),
    path('results/', views.results, name='results'),
]
