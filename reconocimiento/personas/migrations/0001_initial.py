# Generated by Django 5.2.2 on 2025-06-26 04:54

import django.db.models.deletion
import pgvector.django.vector
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sedes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EstudianteFoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagen', models.ImageField(upload_to='estudiantes/fotos_extra/')),
                ('embedding', pgvector.django.vector.VectorField(dimensions=512)),
                ('es_base', models.BooleanField(default=False)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fotos', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EstudianteAsignaturaSeccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asignatura', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sedes.asignatura')),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relaciones_asignatura_seccion', to=settings.AUTH_USER_MODEL)),
                ('seccion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relaciones_estudiantes_asignatura', to='sedes.seccion')),
            ],
            options={
                'unique_together': {('estudiante', 'asignatura')},
            },
        ),
    ]
