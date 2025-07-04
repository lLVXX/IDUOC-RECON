#clases/forms.py

from django import forms
from .models import Aula, BloqueHorario, Clase
from sedes.models import  Seccion, Carrera, Asignatura
from personas.models import CustomUser
from core.models import SemanaAcademica






class AulaForm(forms.ModelForm):
    class Meta:
        model = Aula
        # Sólo estos dos; la vista asigna .sede, y descripción puede quedar vacía
        fields = ['numero_sala', 'camara_ip']
        widgets = {
            'camara_ip': forms.TextInput(attrs={'placeholder': '0 para cámara local'}),
        }
        labels = {
            'numero_sala': 'Número de sala',
            'camara_ip': 'IP de la cámara',
        }
    
class BloqueHorarioForm(forms.ModelForm):
    class Meta:
        model = BloqueHorario
        fields = ['nombre', 'hora_inicio', 'hora_fin']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }


DIAS_SEMANA = [
    ('LU', 'Lunes'),
    ('MA', 'Martes'),
    ('MI', 'Miércoles'),
    ('JU', 'Jueves'),
    ('VI', 'Viernes'),
    ('SA', 'Sábado'),
]


class SeccionModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Muestra más info al usuario
        return f"{obj.nombre} - {obj.asignatura.nombre} - {obj.asignatura.carrera.nombre}"


class PublicarHorarioForm(forms.Form):
    """Para elegir la semana de corte al fijar el horario."""
    effective_from = forms.ModelChoiceField(
        queryset=SemanaAcademica.objects.all().order_by('numero'),
        label="A partir de la semana",
        help_text="Esta versión se aplicará en esta semana y en las siguientes."
    )





class ClaseForm(forms.ModelForm):
    asignatura     = forms.ModelChoiceField(Asignatura.objects.none(), widget=forms.Select)
    seccion        = forms.ModelChoiceField(Seccion.objects.none(),    widget=forms.Select)
    aula           = forms.ModelChoiceField(Aula.objects.none(),       widget=forms.Select)
    dia_semana     = forms.ChoiceField(choices=Clase.DIAS_SEMANA,       widget=forms.Select)
    bloque_horario = forms.ModelChoiceField(BloqueHorario.objects.all(), widget=forms.Select)

    class Meta:
        model  = Clase
        fields = ['asignatura','seccion','aula','dia_semana','bloque_horario']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # 1) limitar asignaturas y aulas por sede
        if user and hasattr(user, 'sede'):
            sede = user.sede
            self.fields['asignatura'].queryset = Asignatura.objects.filter(carrera__sede=sede)
            self.fields['aula'].queryset       = Aula.objects.filter(sede=sede)
        else:
            self.fields['asignatura'].queryset = Asignatura.objects.all()
            self.fields['aula'].queryset       = Aula.objects.all()

        # 2) si hay datos POST (el usuario acaba de elegir asignatura),
        #    repoblamos seccion:
        asignatura_id = self.data.get('asignatura') or self.initial.get('asignatura')
        if asignatura_id:
            self.fields['seccion'].queryset = Seccion.objects.filter(asignatura_id=asignatura_id)
        else:
            # mantenemos vacío al inicio
            self.fields['seccion'].queryset = Seccion.objects.none()
            

class ExcepcionForm(forms.Form):
    semana            = forms.ModelChoiceField(
        queryset=SemanaAcademica.objects.all().order_by('numero'),
        widget=forms.Select(attrs={'class':'form-select'})
    )
    aplicar_restantes = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class':'form-check-input'})
    )
            
#################### ASIS MANUAL #############3


class AsistenciaManualForm(forms.Form):
    def __init__(self, estudiantes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for estudiante in estudiantes:
            self.fields[f"presente_{estudiante.id}"] = forms.BooleanField(
                label=estudiante.get_full_name(),
                required=False,
                initial=False
            )



class PublicarHorarioForm(forms.Form):
    """Para elegir la semana de corte al fijar el horario."""
    effective_from = forms.ModelChoiceField(
        queryset=SemanaAcademica.objects.all().order_by('numero'),
        label="A partir de la semana",
        help_text="Se crearán instancias de clase en esta semana y en las siguientes."
    )
