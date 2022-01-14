from django.urls import path
from . import views

app_name = "parse"

urlpatterns = [
    path('', views.ParseLink.as_view(), name="parse"),
]