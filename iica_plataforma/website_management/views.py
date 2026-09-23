from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
# from django.core.paginator import Paginator
from .models import Noticia

from .forms import (
    LoginForm,
    CreateUserForm,
    CustomUserChangeForm
)





def home(request):
    page_number = request.GET.get("page", 1)
    
    # Consultar exclusivamente la base de datos, ordenadas por fecha o score
    queryset = Noticia.objects.filter(activa=True).order_by('-fecha_publicacion', '-score')
    
    paginator = Paginator(queryset, 6)  # 6 noticias por página
    page_obj = paginator.get_page(page_number)

    return render(request, "website_management/index.html", {
        "noticias": page_obj,
        "page": page_obj.number,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
    })


class Login(FormView):
    template_name = "website_management/login.html"
    form_class = LoginForm
    success_url = reverse_lazy("Inicio")

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):

        if getattr(settings, "USE_MICROSOFT_AUTH", False):
            return redirect("/accounts/login/")

        if request.user.is_authenticated:
            return HttpResponseRedirect(
                self.get_success_url()
            )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super().form_valid(form)


def logoutUsuario(request):
    logout(request)

    if getattr(settings, "USE_MICROSOFT_AUTH", False):
        return redirect("/accounts/logout/")

    return redirect("/accounts/login/")


class SignUp(generic.CreateView):
    template_name = "website_management/signup.html"
    model = User
    form_class = CreateUserForm
    success_url = reverse_lazy("Login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["USE_MICROSOFT_AUTH"] = (
            settings.USE_MICROSOFT_AUTH
        )
        return context


@login_required
def edit_profile(request):

    if request.method == "POST":
        user_form = CustomUserChangeForm(
            request.POST,
            request.FILES,
            instance=request.user
        )

        if user_form.is_valid():
            user = user_form.save()

            profile = request.user.userprofile

            if "profile_image" in request.FILES:
                profile.profile_image = (
                    request.FILES["profile_image"]
                )

            profile.save()
            user.save()

            return redirect("/")

    else:
        user_form = CustomUserChangeForm(
            instance=request.user
        )

    return render(
        request,
        "website_management/edit_profile.html",
        {"user_form": user_form}
    )


@login_required
def edit_password(request):

    if request.method == "POST":
        password_form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if password_form.is_valid():
            password_form.save()
            return redirect("/")

    else:
        password_form = PasswordChangeForm(
            request.user
        )

    return render(
        request,
        "website_management/password.html",
        {"password_form": password_form}
    )