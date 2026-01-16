from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from website_management.views import home, Login, logoutUsuario, SignUp, edit_profile, edit_password

urlpatterns = [
    path('', home, name = "Inicio"),
    path('accounts/login/', Login.as_view(), name = "Login"),
    path('logout/', login_required(logoutUsuario), name = "Logout"),
    path('signup/', SignUp.as_view(), name = "SignUp"),
    path('edit_profile/', edit_profile, name='edit_profile'),
    path('edit_password/', edit_password, name='password'),
]

urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
