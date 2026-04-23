from django.db import migrations

SQL_ADD = """
ALTER TABLE accounts_user
  ADD COLUMN pegawai_ref_id BIGINT NULL AFTER pegawai_id;
"""

SQL_FK = """
ALTER TABLE accounts_user
  ADD CONSTRAINT fk_accounts_user_pegawai_ref
  FOREIGN KEY (pegawai_ref_id) REFERENCES mst_datapegawai(id);
"""

SQL_FILL = """
UPDATE accounts_user u
JOIN mst_datapegawai p ON p.nip = u.pegawai_id
SET u.pegawai_ref_id = p.id
WHERE u.pegawai_id IS NOT NULL AND u.pegawai_id <> '';
"""

SQL_ROLLBACK = """
ALTER TABLE accounts_user DROP FOREIGN KEY fk_accounts_user_pegawai_ref;
ALTER TABLE accounts_user DROP COLUMN pegawai_ref_id;
"""

class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_failed_login_count_user_lockout_until_and_more"),
    ]

    operations = [
        migrations.RunSQL(SQL_ADD, reverse_sql=SQL_ROLLBACK),
        migrations.RunSQL(SQL_FK, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(SQL_FILL, reverse_sql=migrations.RunSQL.noop),
    ]
