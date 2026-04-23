from django import forms
from .models import MstDataPegawai
from core.crypto import hash_lookup

class MstDataPegawaiAdminForm(forms.ModelForm):
    class Meta:
        model = MstDataPegawai
        widgets = {
            "nip": forms.TextInput(attrs={"class": "vTextField", "size": 40}),
            "nik": forms.TextInput(attrs={"class": "vTextField", "size": 40}),
            "nama_lengkap": forms.TextInput(attrs={"class": "vTextField", "size": 80}),
        }
        fields = (
            "nip","nik","nama_lengkap",
            "id_instansi","id_jabatan","is_active",
            "tempat_lahir","tgl_lahir","golongan","eselon","pendidikan","keterangan",
        )

    def clean_nip(self):
        v = (self.cleaned_data.get("nip") or "").strip().replace(" ", "")
        return v or None

    def clean_nik(self):
        v = (self.cleaned_data.get("nik") or "").strip().replace(" ", "")
        return v or None

    def clean_nama_lengkap(self):
        v = (self.cleaned_data.get("nama_lengkap") or "").strip()
        return v or None

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.nip_hash = hash_lookup(obj.nip) if obj.nip else None
        obj.nik_hash = hash_lookup(obj.nik) if obj.nik else None
        obj.nama_lengkap_hash = hash_lookup(obj.nama_lengkap) if obj.nama_lengkap else None
        if commit:
            obj.save()
            self.save_m2m()
        return obj
