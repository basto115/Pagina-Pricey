
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', views.vista_login, name='login'),
    path('registro/', views.vista_registro, name='registro'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('mi-cuenta/', views.mi_cuenta, name='mi_cuenta'),
    path('mi-cuenta/editar/', views.editar_cuenta, name='editar_cuenta'),


    # Recuperación de contraseña
    path(
        'recuperar-contrasena/',
        auth_views.PasswordResetView.as_view(
            template_name='farmacia/password_reset.html',
            email_template_name='farmacia/password_reset_email.txt',
            html_email_template_name='farmacia/password_reset_email.html',
            subject_template_name='farmacia/password_reset_subject.txt',
            success_url='/recuperar-contrasena/enviado/'
        ),
        name='password_reset'
    ),
    path(
        'recuperar-contrasena/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='farmacia/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'restablecer-contrasena/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='farmacia/password_reset_confirm.html',
            success_url='/restablecer-contrasena/completado/'
        ),
        name='password_reset_confirm'
    ),
    path(
        'restablecer-contrasena/completado/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='farmacia/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

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
    path('mi-lista/agregar/<int:producto_id>/', views.agregar_a_lista, name='agregar_a_lista'),
    path('mi-lista/modificar/<int:producto_id>/', views.modificar_cantidad_lista, 
         name='modificar_cantidad_lista'),
    path('mi-lista/eliminar/<int:producto_id>/', views.eliminar_de_lista, name='eliminar_de_lista'),
    path('mi-lista/planificar-ruta/', views.planificar_ruta, name='planificar_ruta'),
    
]
