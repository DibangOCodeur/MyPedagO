from django.contrib import admin
from django.urls import path, include
from Utilisateur import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='connexion'),
    path('logout/', views.logout_view, name='deconnexion'),
    path('password_reset/', views.user_change_password, name='mot_de_passe_oublie'),
    path('admin/', admin.site.urls),
    path('utilisateur/', include('Utilisateur.urls')),
    path('gestion/', include('Gestion.urls')),
    ]


# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)