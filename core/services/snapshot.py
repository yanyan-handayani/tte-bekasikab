from core.models import MstDataPegawai


def snapshot_jabatan_from_pegawai(pegawai) -> str | None:
    """
    Ambil nama jabatan untuk disimpan sebagai snapshot.
    """
    if not pegawai:
        return None
    j = getattr(pegawai, "id_jabatan", None)
    if not j:
        return None
    # sesuaikan field nama jabatan di model MstJabatan kamu
    return (getattr(j, "nama_jabatan", None) or "").strip() or None
