# TTE Django Backend (mapping awal)

Project Django ini fokus untuk **mapping DDL legacy** supaya:
- Model kebaca di Django ORM
- Bisa dikelola dari **Django Admin** (CRUD dasar)
- Siap dilanjutkan ke tahap normalisasi + API (DRF) + Vue

## Cara jalanin

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env sesuai MySQL kamu

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Buka: http://127.0.0.1:8000/admin/

## Catatan mapping penting

- `mst_jabatan` di DDL memakai **composite primary key** `(id_jabatan, id_instansi, id_parent)`.
  Django tidak support composite PK → `id_jabatan` jadi PK, dan kombinasi tetap dijaga via `unique_together`.

- tabel `user` adalah legacy (nama tabel reserved). Model: `TteUser` dengan `db_table="user"`.
  Untuk autentikasi Django, rekomendasi next step: bikin CustomUser terpisah lalu migrasi data.
