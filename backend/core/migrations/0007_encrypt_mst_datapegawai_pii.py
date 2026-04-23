# core/migrations/0007_encrypt_mst_datapegawai_pii.py
from django.db import migrations

BATCH_SIZE = 500


def forwards(apps, schema_editor):
    # Import helper runtime (pakai key dari settings)
    from core.crypto import encrypt_str, hash_lookup

    with schema_editor.connection.cursor() as cursor:
        # Pastikan legacy_nip terisi (buat relasi legacy yang masih pakai NIP)
        cursor.execute(
            """
            UPDATE mst_datapegawai
            SET legacy_nip = nip
            WHERE legacy_nip IS NULL
            """
        )

        # Ambil jumlah rows yang perlu diproses
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM mst_datapegawai
            WHERE nip_enc IS NULL
               OR nip_hash IS NULL
               OR (nik IS NOT NULL AND nik_enc IS NULL)
               OR (nama_lengkap IS NOT NULL AND nama_lengkap_enc IS NULL)
               OR (nik IS NOT NULL AND nik_hash IS NULL)
               OR (nama_lengkap IS NOT NULL AND nama_lengkap_hash IS NULL)
            """
        )
        total = cursor.fetchone()[0]

        offset = 0
        while True:
            cursor.execute(
                f"""
                SELECT id, nip, nik, nama_lengkap, nip_enc, nik_enc, nama_lengkap_enc
                FROM mst_datapegawai
                ORDER BY id
                LIMIT {BATCH_SIZE} OFFSET {offset}
                """
            )
            rows = cursor.fetchall()
            if not rows:
                break

            updates = []
            for (pid, nip, nik, nama, nip_enc, nik_enc, nama_enc) in rows:
                # hitung nilai target
                new_nip_enc = nip_enc or (encrypt_str(nip) if nip else None)
                new_nik_enc = nik_enc or (encrypt_str(nik) if nik else None)
                new_nama_enc = nama_enc or (encrypt_str(nama) if nama else None)

                new_nip_hash = hash_lookup(nip) if nip else None
                new_nik_hash = hash_lookup(nik) if nik else None
                new_nama_hash = hash_lookup(nama) if nama else None

                updates.append((
                    new_nip_enc, new_nip_hash,
                    new_nik_enc, new_nik_hash,
                    new_nama_enc, new_nama_hash,
                    pid
                ))

            # Update batch (hanya menimpa kolom enc/hash; plaintext tidak diubah di tahap A)
            cursor.executemany(
                """
                UPDATE mst_datapegawai
                SET
                  nip_enc = COALESCE(nip_enc, %s),
                  nip_hash = COALESCE(nip_hash, %s),
                  nik_enc = COALESCE(nik_enc, %s),
                  nik_hash = COALESCE(nik_hash, %s),
                  nama_lengkap_enc = COALESCE(nama_lengkap_enc, %s),
                  nama_lengkap_hash = COALESCE(nama_lengkap_hash, %s)
                WHERE id = %s
                """,
                updates
            )

            offset += BATCH_SIZE


def backwards(apps, schema_editor):
    # rollback aman: cukup kosongkan kolom enc/hash (plaintext masih ada)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE mst_datapegawai
            SET
              nip_enc = NULL, nip_hash = NULL,
              nik_enc = NULL, nik_hash = NULL,
              nama_lengkap_enc = NULL, nama_lengkap_hash = NULL
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_mstdatapegawai_id_mstdatapegawai_nama_lengkap_hash"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
