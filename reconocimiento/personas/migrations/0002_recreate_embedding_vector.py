# personas/migrations/0002_recreate_embedding_vector.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0001_initial'),
    ]

    operations = [
        # 1) Elimina la columna antigua
        migrations.RunSQL(
            sql="ALTER TABLE personas_estudiantefoto DROP COLUMN embedding;",
            reverse_sql="ALTER TABLE personas_estudiantefoto ADD COLUMN embedding bytea;"
        ),
        # 2) Añade la nueva columna vector(512)
        migrations.RunSQL(
            sql="ALTER TABLE personas_estudiantefoto ADD COLUMN embedding vector(512);",
            reverse_sql="ALTER TABLE personas_estudiantefoto DROP COLUMN embedding;"
        ),
    ]
