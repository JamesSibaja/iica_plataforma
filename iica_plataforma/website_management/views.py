from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .forms import LoginForm, CreateUserForm, CustomUserChangeForm
from django.contrib.auth.decorators import login_required
# import paramiko
# import os
# from .models import UserProfile

def home(request):
    return render(request, "website_management/index.html")

class Login(FormView):
    template_name = "website_management/login.html"
    form_class = LoginForm
    success_url = reverse_lazy('project-list')

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(self.get_success_url())
        else:
            return super(Login, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super(Login, self).form_valid(form)

def logoutUsuario(request):
    logout(request)
    return HttpResponseRedirect('/accounts/login/')

class SignUp(generic.CreateView):
    template_name = "website_management/signup.html"
    model = User
    form_class = CreateUserForm
    success_url = reverse_lazy ('Login')

    def form_valid(self,form):
        return super(SignUp,self).form_valid(form)

# class SignUp(generic.CreateView):
#     template_name = "website_management/signup.html"
#     form_class = CreateUserForm
#     success_url = reverse_lazy('Login')

#     def form_valid(self, form):
#         response = super().form_valid(form)
#         generate_ssh_keys(self.object)
#         return response

# def generate_ssh_keys(user):
#     # Generar par de claves SSH
#     key = paramiko.RSAKey.generate(2048)
    
#     # Almacenar la clave pública en la base de datos
#     try:
#         profile = user.userprofile
#     except UserProfile.DoesNotExist:
#         profile = UserProfile.objects.create(user=user)
#     profile.ssh_public_key = key.get_base64()
#     profile.save()
    
#     # Guardar la clave privada en el servidor
#     private_key_path = f'/etc/ssh/keys/{user.username}_private.pem'
#     os.makedirs('/etc/ssh/keys', exist_ok=True)  # Crear directorio si no existe
#     with open(private_key_path, 'w') as private_key_file:
#         key.write_private_key(private_key_file)

    # return private_key_path

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if user_form.is_valid():
            user = user_form.save()
            user_profile = request.user.userprofile
            if 'profile_image' in request.FILES:
                profile_image = request.FILES['profile_image']
                user_profile.profile_image = profile_image
            user_profile.save()
            user.save()
            # Agrega la lógica para guardar otros campos del UserProfile aquí
            return redirect('/project/')
    else:
        user_form = CustomUserChangeForm(instance=request.user)
    
    return render(request, 'website_management/edit_profile.html', {'user_form': user_form})

@login_required
def edit_password(request):
    if request.method == 'POST':
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            password_form.save()
            # Agrega la lógica para guardar otros campos del UserProfile aquí
            return redirect('/project/')
    else:
        password_form = PasswordChangeForm(request.user)
    
    return render(request, 'website_management/password.html', {'password_form': password_form})

# @login_required
# def edit_profile(request):
#     if request.method == 'POST':
#         form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
#         if form.is_valid():
#             user = form.save()
#             user_profile = request.user.userprofile

#             if 'profile_image' in request.FILES:
#                 profile_image = request.FILES['profile_image']
#                 user_profile.profile_image = profile_image

#         # Puedes guardar otros campos del UserProfile aquí

#             user_profile.save()
#             # new_password = form.cleaned_data.get('new_password1')
#             # if new_password:
#             #     user.set_password(new_password)
#             user.save()
#             return redirect('/project/')
#             # Realiza acciones adicionales si es necesario
#     else:
#         form = CustomUserChangeForm(instance=request.user)
    
#     return render(request, 'website_management/edit_profile.html', {'form': form})