from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Distribuidor, Revendedor, UsuarioFinal, Vehicle, SIMAssignation, SimCard
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re

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

User = get_user_model()

def generate_password(first_name, last_name, phone_number, rfc):
    base = (
        first_name[:2].upper() +
        last_name[:2].lower() +
        phone_number[-4:]
    )

    password = f"{base}!{rfc[-2:]}"
    return password

class DistribuidorForm(forms.ModelForm):

    class Meta:
        model = Distribuidor
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'rfc', 'company',
            'street', 'city', 'state', 'zip', 'country'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre*'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Apellido*'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Correo electrónico*'
        })
        self.fields['rfc'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'RFC*'
        })
        self.fields['company'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre de la empresa*'
        })
        self.fields['street'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Dirección*'
        })
        self.fields['city'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ciudad*'
        })
        self.fields['state'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Estado/Provincia*'
        })
        self.fields['zip'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Código postal*'
        })
        self.fields['country'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'País*'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Número de Whatsapp*'
        })
    
    def cleaned_phone_number(self):
            phone = self.cleaned_data.get('phone_number', '').strip()
            phone = re.sub(r'\D', '', phone)
            if len(phone) != 10:
                self.add_error('phone_number', 'El número debe tener exactamente 10 dígitos.')
            return phone

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email').strip()
        phone = self.cleaned_phone_number()
        if User.objects.filter(email=email).exists():
            self.add_error('email', 'Este correo electrónico ya está registrado.')
        if UsuarioFinal.objects.filter(phone_number=phone).exists():
            self.add_error('phone_number', 'Este número telefónico ya está registrado.')
        return cleaned_data
    
    def save(self, commit=True):

        password = generate_password(self.cleaned_data['first_name'], self.cleaned_data['last_name'], 
                                    self.cleaned_data['phone_number'], self.cleaned_data['rfc'])
        
        user = User.objects.create_user(
            username=self.cleaned_data['email'].strip(),
            password=password.strip(),
            first_name=self.cleaned_data['first_name'].strip(),
            last_name=self.cleaned_data['last_name'].strip(),
            email=self.cleaned_data['email'].strip(),
            user_type='DISTRIBUIDOR'
        )

        distribuidor = super().save(commit=False)   
        distribuidor.user = user

        if commit:
            distribuidor.save()
        
        return distribuidor

class RevendedorForm(forms.ModelForm):

    class Meta:
        model = Revendedor
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'rfc', 'company',
            'street', 'city', 'state', 'zip', 'country'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre*'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Apellido*'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Correo electrónico*'
        })
        self.fields['rfc'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'RFC*'
        })
        self.fields['company'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre de la empresa*'
        })
        self.fields['street'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Dirección*'
        })
        self.fields['city'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ciudad*'
        })
        self.fields['state'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Estado/Provincia*'
        })
        self.fields['zip'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Código postal*'
        })
        self.fields['country'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'País*'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Número de Whatsapp*'
        })
    
    def cleaned_phone_number(self):
            phone = self.cleaned_data.get('phone_number', '').strip()
            phone = re.sub(r'\D', '', phone)
            if len(phone) != 10:
                self.add_error('phone_number', 'El número debe tener exactamente 10 dígitos.')
            return phone

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email').strip()
        phone = self.cleaned_phone_number()
        if User.objects.filter(email=email).exists():
            self.add_error('email', 'Este correo electrónico ya está registrado.')
        if UsuarioFinal.objects.filter(phone_number=phone).exists():
            self.add_error('phone_number', 'Este número telefónico ya está registrado.')
        return cleaned_data

    def save(self, commit=True, distribuidor_id=None):

        password = password = generate_password(self.cleaned_data['first_name'], self.cleaned_data['last_name'], 
                                    self.cleaned_data['phone_number'], self.cleaned_data['rfc'])

        user = User.objects.create_user(
            username=self.cleaned_data['email'].strip(),
            password=password.strip(),
            first_name=self.cleaned_data['first_name'].strip(),
            last_name=self.cleaned_data['last_name'].strip(),
            email=self.cleaned_data['email'].strip(),
            user_type='REVENDEDOR'
        )

        revendedor = super().save(commit=False)   
        revendedor.user = user

        if distribuidor_id is not None:
            revendedor.distribuidor = Distribuidor.objects.get(id=distribuidor_id)

        if commit:
            revendedor.save()
        
        return revendedor

class ClienteForm(forms.ModelForm):

    class Meta:
        model = UsuarioFinal
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'company',
            'street', 'city', 'state', 'zip', 'country'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre*'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Apellido*'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control not-required',
            'placeholder': 'Correo electrónico'
        })
        self.fields['company'].widget.attrs.update({
            'class': 'form-control not-required',
            'placeholder': 'Nombre de la empresa'
        })
        self.fields['street'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Dirección*'
        })
        self.fields['city'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ciudad*'
        })
        self.fields['state'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Estado/Provincia*'
        })
        self.fields['zip'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Código postal*'
        })
        self.fields['country'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'País*'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Número de Whatsapp*'
        })
    

    def cleaned_phone_number(self):
            phone = self.cleaned_data.get('phone_number', '').strip()
            phone = re.sub(r'\D', '', phone)
            if len(phone) != 10:
                self.add_error('phone_number', 'El número debe tener exactamente 10 dígitos.')
            return phone

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email').strip()
        phone = self.cleaned_phone_number()
        if User.objects.filter(email=email).exists():
            self.add_error('email', 'Este correo electrónico ya está registrado.')
        if UsuarioFinal.objects.filter(phone_number=phone).exists():
            self.add_error('phone_number', 'Este número telefónico ya está registrado.')
        return cleaned_data

    def save(self, commit=True, revendedor_id=None, distribuidor_id=None):

        password = (self.cleaned_data['last_name'][:2] + self.cleaned_data['first_name'][:2] + self.cleaned_data['phone_number'][-4:])

        user = User.objects.create_user(
            username=self.cleaned_data['email'].strip(),
            password=password.strip(),
            first_name=self.cleaned_data['first_name'].strip(),
            last_name=self.cleaned_data['last_name'].strip(),
            email=self.cleaned_data['email'].strip(),
            user_type='FINAL'
        )

        cliente = super().save(commit=False)   
        cliente.user = user

        if revendedor_id is not None:
            cliente.revendedor = Revendedor.objects.get(id=revendedor_id)

        if distribuidor_id is not None:
            cliente.distribuidor = Distribuidor.objects.get(id=distribuidor_id)

        if commit:
            cliente.save()
        
        return cliente
