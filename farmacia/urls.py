
from django.urls import path
from . import views


urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', views.vista_login, name='login'),
    path('registro/', views.vista_resgitro, name='registro'),

    path(
        'medicamento/<int:medicamento_id>/',
        views.detalle_medicamento,
        name='detalle_medicamento'
    ),

    path(
        'api/farmacias/',
        views.listar_farmacias,
        name='listar_farmacias'
    ),

    path(
        'api/precios/',
        views.listar_precios,
        name='listar_precios'
    ),

    path(
        'api/medicamentos/',
        views.api_medicamentos,
        name='api_medicamentos'
    ),
    
    path('leer-receta/', views.leer_receta, name='leer_receta'),
    path('mi-lista/', views.ver_lista, name='ver_lista'),
]
