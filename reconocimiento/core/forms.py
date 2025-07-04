# core/forms.py

from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
import re
from .models import CalendarioAcademico,SemanaAcademica
from core.models import CustomUser
from sedes.models import Sede



class CustomLoginForm(forms.Form):
    identificador = forms.CharField(label='Correo o Usuario')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

    def clean(self):
        identificador = self.cleaned_data.get("identificador")
        password = self.cleaned_data.get("password")

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(email=identificador)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=identificador)
            except User.DoesNotExist:
                user = None

        if user:
            auth_user = authenticate(username=user.username, password=password)
        else:
            auth_user = None

        if auth_user is None:
            raise ValidationError("Credenciales inválidas.")
        self.cleaned_data['user'] = auth_user
        return self.cleaned_data



################################################################3


def validar_rut_chileno(rut):
    rut = rut.replace(".", "").replace("-", "").upper()
    if not re.match(r'^\d{7,8}[0-9K]$', rut):
        raise forms.ValidationError("El RUT debe tener el formato 12.345.678-9")
    return rut

class AdminZonaForm(forms.ModelForm):
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'})
    )
    apellido = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'})
    )
    rut = forms.CharField(
        validators=[validar_rut_chileno],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12.345.678-9', 'id': 'rut-input'})
    )
    sede = forms.ModelChoiceField(
        queryset=Sede.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = ['nombre', 'apellido', 'rut', 'sede']


########## Calendario ############


class CalendarioWizardForm(forms.Form):
    sede = forms.ModelChoiceField(queryset=None)
    nombre = forms.CharField(label="Nombre del Calendario", max_length=100)
    fecha_inicio = forms.DateField(label="Fecha de inicio del semestre", widget=forms.DateInput(attrs={'type':'date'}))
    semanas = forms.IntegerField(label="Cantidad de semanas", initial=18, min_value=1, max_value=25)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Limita a sede del admin_zona, o todas si admin_global
        if user and hasattr(user, 'sede') and user.user_type == 'admin_zona':
            self.fields['sede'].queryset = Sede.objects.filter(id=user.sede.id)
            self.fields['sede'].initial = user.sede
            self.fields['sede'].widget = forms.HiddenInput()
        else:
            self.fields['sede'].queryset = Sede.objects.all()


#######################

class CalendarioGlobalForm(forms.Form):
    nombre = forms.CharField(label="Nombre del Calendario", max_length=100)
    fecha_inicio = forms.DateField(label="Fecha de inicio", widget=forms.DateInput(attrs={'type': 'date'}))
    semanas = forms.IntegerField(label="Cantidad de semanas", min_value=1, max_value=25, initial=18)


class EditarCalendarioForm(forms.ModelForm):
    class Meta:
        model = CalendarioAcademico
        fields = ['nombre', 'fecha_inicio', 'fecha_fin']

class EditarSemanaForm(forms.ModelForm):
    class Meta:
        model = SemanaAcademica
        fields = ['numero', 'fecha_inicio', 'fecha_fin', 'tipo', 'descripcion']