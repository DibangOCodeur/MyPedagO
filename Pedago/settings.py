# ========================================
# CONFIGURATION POUR DÉVELOPPEMENT LOCAL
# settings.py ou settings/development.py
# ========================================

import os
from pathlib import Path


# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'votre-secret-key-ici-changez-en-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '*']


# ========================================
# CONFIGURATION DES APPLICATIONS
# ========================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', 
    'django.contrib.humanize',
    'django_countries',

    
    # Votre application
    'Utilisateur',
    'Gestion',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'Utilisateur.middleware.RoleBasedRedirectMiddleware',
]

ROOT_URLCONF = 'Pedago.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'Pedago.wsgi.application'


# ========================================
# BASE DE DONNÉES
# ========================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ========================================
# VALIDATION DES MOTS DE PASSE
# ========================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ========================================
# INTERNATIONALISATION
# ========================================

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True


# ========================================
# FICHIERS MEDIA (uploads utilisateurs)
# ========================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ========================================
# FICHIERS STATIQUES (CSS, JavaScript, Images)
# ========================================

STATIC_URL = '/static/'

# ✅ CONFIGURATION CORRIGÉE
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Pour la production (commenté en développement)
# STATIC_ROOT = BASE_DIR / 'staticfiles'

# Configuration des finders pour localiser les fichiers statiques
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]


# ========================================
# CONFIGURATION UTILISATEUR PERSONNALISÉ
# ========================================

AUTH_USER_MODEL = 'Utilisateur.CustomUser'


# ========================================
# CONFIGURATION D'AUTHENTIFICATION
# ========================================

# URLs de redirection
LOGIN_URL = 'connexion'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'connexion'


# ========================================
# CONFIGURATION DES UPLOADS
# ========================================

# Taille maximale des fichiers uploadés (10MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Configuration du stockage des fichiers
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Permissions des fichiers uploadés
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Types de fichiers acceptés (optionnel - validation supplémentaire)
ALLOWED_FILE_EXTENSIONS = {
    'image': ['.jpg', '.jpeg', '.png'],
    'document': ['.pdf', '.doc', '.docx'],
}

ALLOWED_MIME_TYPES = {
    'image': ['image/jpeg', 'image/png'],
    'document': ['application/pdf', 'application/msword', 
                 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
}


# ========================================
# CONFIGURATION EMAIL
# ========================================

# Pour le développement (console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Pour la production (décommentez et configurez)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'votre-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'votre-mot-de-passe-application'
# DEFAULT_FROM_EMAIL = 'IIPEA <votre-email@gmail.com>'

# Configuration optionnelle
ADMIN_EMAIL = 'admin@iipea.edu.ci'
SITE_URL = 'http://127.0.0.1:8000'  # ✅ Changé pour le développement


# ========================================
# DEFAULT AUTO FIELD (recommandé pour Django 3.2+)
# ========================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Créer le dossier logs s'il n'existe pas
import os
if not os.path.exists('logs'):
    os.makedirs('logs')

# ==========================================
# SESSION CONFIGURATION
# ==========================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 heures
SESSION_SAVE_EVERY_REQUEST = False

# ==========================================
# CORS CONFIGURATION (si nécessaire)
# ==========================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://myiipea.ci",
]

CORS_ALLOW_CREDENTIALS = True

# ==========================================
# API EXTERNE CONFIGURATION
# ==========================================
MYIIPEA_API_BASE_URL = "https://myiipea.ci/api"
MYIIPEA_API_TIMEOUT = 30  # secondes
MYIIPEA_CACHE_TIMEOUT = 300  # 5 minutes













# # ========================================
# # CONFIGURATION POUR DÉVELOPPEMENT LOCAL
# # settings.py ou settings/development.py
# # ========================================

# import os
# from pathlib import Path


# # Build paths
# BASE_DIR = Path(__file__).resolve().parent.parent

# # SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'votre-secret-key-ici-changez-en-production'

# # SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True

# ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '*']


# # ========================================
# # CONFIGURATION DES APPLICATIONS
# # ========================================

# INSTALLED_APPS = [
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
    
#     # Votre application
#     'Utilisateur',  # Remplacez par le nom de votre app
# ]

# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',

#     'Utilisateur.middleware.RoleBasedRedirectMiddleware',

# ]

# ROOT_URLCONF = 'Pedago.urls'  # Remplacez par le nom de votre projet

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates'],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]

# WSGI_APPLICATION = 'Pedago.wsgi.application'


# # ========================================
# # BASE DE DONNÉES
# # ========================================

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }



# # ========================================
# # VALIDATION DES MOTS DE PASSE
# # ========================================

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#         'OPTIONS': {
#             'min_length': 8,
#         }
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]


# # ========================================
# # INTERNATIONALISATION
# # ========================================

# LANGUAGE_CODE = 'fr-fr'
# TIME_ZONE = 'Africa/Abidjan'
# USE_I18N = True
# USE_TZ = True


# # ========================================
# # FICHIERS STATIQUES (CSS, JavaScript, Images)
# # ========================================

# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# # ========================================
# # FICHIERS STATIQUES (CSS, JavaScript, Images)
# # ========================================

# STATIC_URL = '/static/'

# # Pour le développement
# if DEBUG:
#     STATICFILES_DIRS = [
#         BASE_DIR / 'static',
#     ]
# else:
#     # Pour la production
#     STATIC_ROOT = BASE_DIR / 'staticfiles'

# # Configuration supplémentaire pour les fichiers statiques
# STATICFILES_FINDERS = [
#     'django.contrib.staticfiles.finders.FileSystemFinder',
#     'django.contrib.staticfiles.finders.AppDirectoriesFinder',
# ]
# # ========================================
# # CONFIGURATION UTILISATEUR PERSONNALISÉ
# # ========================================

# AUTH_USER_MODEL = 'Utilisateur.CustomUser'  # Remplacez par votre app


# # ========================================
# # CONFIGURATION D'AUTHENTIFICATION
# # ========================================

# # URLs de redirection
# LOGIN_URL = 'connexion'
# LOGIN_REDIRECT_URL = 'dashboard'
# LOGOUT_REDIRECT_URL = 'connexion'

# # Taille maximale des fichiers uploadés (10MB)
# DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
# FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# # Configuration du stockage des fichiers
# DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# # Permissions des fichiers uploadés
# FILE_UPLOAD_PERMISSIONS = 0o644
# FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# # Types de fichiers acceptés (optionnel - validation supplémentaire)
# ALLOWED_FILE_EXTENSIONS = {
#     'image': ['.jpg', '.jpeg', '.png'],
#     'document': ['.pdf', '.doc', '.docx'],
# }

# ALLOWED_MIME_TYPES = {
#     'image': ['image/jpeg', 'image/png'],
#     'document': ['application/pdf', 'application/msword', 
#                  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
# }


# # Configuration Email
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'votre-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'votre-mot-de-passe-application'
# DEFAULT_FROM_EMAIL = 'IIPEA <votre-email@gmail.com>'

# # Pour le développement (console)
# # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# # Configuration optionnelle
# ADMIN_EMAIL = 'admin@iipea.edu.ci'
# SITE_URL = 'https://votre-site.com'