#SEDES/FORMS.PY

from django import forms
from .models import Sede
from .models import Carrera
from .models import Seccion, Asignatura


class SedeForm(forms.ModelForm):
    class Meta:
        model = Sede
        fields = ['nombre', 'direccion', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la sede'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción'}),
        }

#############################################################


class CarreraForm(forms.ModelForm):
    class Meta:
        model = Carrera
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

#############################################


class AsignaturaForm(forms.ModelForm):
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Asignatura
        fields = ['nombre', 'carrera']

    def __init__(self, *args, **kwargs):
        sede = kwargs.pop('sede', None)
        super().__init__(*args, **kwargs)
        if sede:
            self.fields['carrera'].queryset = Carrera.objects.filter(sede=sede)


###############################################



class SeccionForm(forms.ModelForm):
    asignatura = forms.ModelChoiceField(
        queryset=Asignatura.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Seccion
        fields = ['nombre', 'asignatura']

    def __init__(self, *args, **kwargs):
        sede = kwargs.pop('sede', None)
        super().__init__(*args, **kwargs)
        if sede:
            self.fields['asignatura'].queryset = Asignatura.objects.filter(carrera__sede=sede)