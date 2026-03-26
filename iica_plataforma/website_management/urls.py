from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from website_management.views import home, edit_profile, edit_password, Login, logoutUsuario, SignUp


urlpatterns = [
    path('', home, name="Inicio"),

    path('edit_profile/', edit_profile, name='edit_profile'),
    path('edit_password/', edit_password, name='password'),
]

# -------------------------
# MODO SIN MICROSOFT (LOGIN NORMAL)
# -------------------------
if not getattr(settings, "USE_MICROSOFT_AUTH", False):
    urlpatterns += [
        path('accounts/login/', Login.as_view(), name="Login"),
        path('logout/', login_required(logoutUsuario), name="Logout"),
        path('signup/', SignUp.as_view(), name='SignUp'),        
    ]

# -------------------------
# MODO MICROSOFT
# -------------------------
if getattr(settings, "USE_MICROSOFT_AUTH", False):
    urlpatterns += [
        path("accounts/", include("allauth.urls")),
    ]

# -------------------------
# MEDIA
# -------------------------
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)