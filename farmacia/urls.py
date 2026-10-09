from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name="inicio"),
]



urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('api/farmacias/', views.listar_farmacias, name='listar_farmacias'),
]