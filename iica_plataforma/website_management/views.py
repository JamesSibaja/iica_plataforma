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
    success_url = reverse_lazy('Inicio')

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
            return redirect('/')
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
            return redirect('/')
    else:
        password_form = PasswordChangeForm(request.user)
    
    return render(request, 'website_management/password.html', {'password_form': password_form})

