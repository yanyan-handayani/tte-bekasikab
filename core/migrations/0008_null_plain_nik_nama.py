from django.db import migrations

def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            UPDATE mst_datapegawai
            SET nik = NULL, nama_lengkap = NULL
            WHERE (nik IS NOT NULL OR nama_lengkap IS NOT NULL)
        """)

def backwards(apps, schema_editor):
    # Tidak bisa restore plaintext tanpa decrypt (sengaja)
    pass

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_encrypt_mst_datapegawai_pii"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
