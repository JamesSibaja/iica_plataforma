from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django import forms


# class CustomUserChangeForm(UserChangeForm):
#                      # profile_image = forms.ImageField(required=False, label='Profile Image')
#     # new_password1 = forms.CharField(widget=forms.PasswordInput, required=False, label='New Password')
#     # new_password2 = forms.CharField(widget=forms.PasswordInput, required=False, label='Confirm New Password')

#     class Meta:
#         model = get_user_model()
#         fields = ['first_name', 'last_name', 'email']

#     # def clean_new_password2(self):
#     #     new_password1 = self.cleaned_data.get('new_password1')
#     #     new_password2 = self.cleaned_data.get('new_password2')
#     #     if new_password1 and new_password1 != new_password2:
#     #         raise forms.ValidationError("Passwords don't match")
#     #     return new_password2
        
class CustomUserChangeForm(UserChangeForm):
    password = None  # Elimina el campo de contraseña de UserChangeForm

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

class CustomPasswordChangeForm(PasswordChangeForm):
    class Meta:
        model = get_user_model()
    
class LoginForm (AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(LoginForm,self).__init__( *args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['username'].widget.attrs['placeholder'] = 'Nombre de usuario'
        self.fields['password'].widget.attrs['class'] = 'form-control'
        self.fields['password'].widget.attrs['placeholder'] = 'Contraseña'

class CreateUserForm(UserCreationForm):
    class Meta:
        model =  User
        fields = ['first_name','last_name','email','username','password1','password2']

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        
