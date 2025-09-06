from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Distribuidor, Revendedor, Cliente, BaseProfile
import re

User = get_user_model()

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form_input',
        'placeholder': 'Correo electrónico'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'id': 'passwordField',
        'class': 'form_input',
        'placeholder': 'Contraseña'
    }))

def generate_password(first_name, last_name, phone_number, rfc=None):
    digits = re.sub(r'\D', '', phone_number)
    base = first_name[:2].upper() + last_name[:2].lower() + digits[-4:]
    if rfc:
        return f"{base}!{rfc[-2:]}"
    return base

class BaseProfileForm(forms.ModelForm):
    dial = forms.CharField(max_length=5, required=True, initial='+52', label='Dial')

    user_type = None
    password_generator = staticmethod(generate_password)

    def __init__(self, *args, lang=None, **kwargs):
        super().__init__(*args, **kwargs)
        if lang is None:
            lang = {}

        placeholders = {**{f: lang.get(f, f.capitalize()) for f in self.Meta.fields}, 'dial': 'Ej. +52'}
        for field, placeholder in placeholders.items():
            css_class = 'form-control dial-input' if field == 'dial' else 'form-control'
            self.fields[field].widget.attrs.update({'class': css_class, 'placeholder': placeholder})

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        phone = re.sub(r'\D', '', phone)
        if len(phone) != 10:
            self.add_error('phone_number', 'El número debe tener exactamente 10 dígitos.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '').strip()
        phone = self.clean_phone_number()
        dial = cleaned_data.get('dial', '').strip()
        full_phone = f"{dial} {phone}"
        cleaned_data['phone_number'] = full_phone

        if User.objects.filter(email=email).exists():
            self.add_error('email', 'Este correo electrónico ya está registrado.')
        if BaseProfile.phone_exists(phone):
            self.add_error('phone_number', 'Este número telefónico ya está registrado.')

        return cleaned_data

    def save_user(self, password=None):
        if password is None:
            password = self.password_generator(
                self.cleaned_data['first_name'],
                self.cleaned_data['last_name'],
                self.cleaned_data['phone_number'],
                self.cleaned_data.get('rfc')
            )
        return User.objects.create_user(
            username=self.cleaned_data['email'].strip(),
            password=password.strip(),
            first_name=self.cleaned_data['first_name'].strip(),
            last_name=self.cleaned_data['last_name'].strip(),
            email=self.cleaned_data['email'].strip(),
            user_type=self.user_type
        )

    def save(self, commit=True, **kwargs):
        user = self.save_user()
        obj = super().save(commit=False)
        obj.user = user
        obj.phone_number = self.cleaned_data['phone_number']

        for key, model_class in [('distribuidor_id', Distribuidor), ('revendedor_id', Revendedor)]:
            if key in kwargs and kwargs[key] is not None:
                setattr(obj, key.replace('_id', ''), model_class.objects.get(id=kwargs[key]))

        if commit:
            obj.save()
        return obj

class DistribuidorForm(BaseProfileForm):
    class Meta:
        model = Distribuidor
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'rfc', 'company', 'street', 'city', 'state', 'zip', 'country']
    user_type = 'DISTRIBUIDOR'

class RevendedorForm(BaseProfileForm):
    class Meta:
        model = Revendedor
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'rfc', 'company', 'street', 'city', 'state', 'zip', 'country']
    user_type = 'REVENDEDOR'

class ClienteForm(BaseProfileForm):
    class Meta:
        model = Cliente
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'company', 'street', 'city', 'state', 'zip', 'country']
    user_type = 'CLIENTE'
