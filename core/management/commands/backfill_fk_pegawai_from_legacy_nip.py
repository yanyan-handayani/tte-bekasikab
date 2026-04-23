from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Asda, AsdaSkpd, MstDataPegawai

class Command(BaseCommand):
    help = "Backfill pegawai_id on ASDA/ASDA_SKPD from legacy NIP columns."

    def handle(self, *args, **options):
        # bangun mapping nip_plain -> pegawai_id
        nip_to_id = {}
        for p in MstDataPegawai.objects.all().only("id", "nip"):
            nip = (p.nip or "").strip()
            if nip:
                nip_to_id[nip] = p.id

        with transaction.atomic():
            # ASDA
            qs = (
                Asda.objects
                .filter(pegawai__isnull=True)
                .exclude(nip_pejabat__isnull=True)
                .exclude(nip_pejabat="")
                .only("id_loc_asda", "nip_pejabat")
            )
            upd = 0
            for row in qs:
                pid = nip_to_id.get((row.nip_pejabat or "").strip())
                if pid:
                    Asda.objects.filter(pk=row.pk).update(pegawai_id=pid)
                    upd += 1
            self.stdout.write(f"ASDA updated: {upd}")

            # ASDA_SKPD
            qs = (
                AsdaSkpd.objects
                .filter(kepala_pegawai__isnull=True)
                .exclude(nip_kepala_skpd__isnull=True)
                .exclude(nip_kepala_skpd="")
                .only("id_asda_skpd", "nip_kepala_skpd")
            )
            upd = 0
            for row in qs:
                pid = nip_to_id.get((row.nip_kepala_skpd or "").strip())
                if pid:
                    AsdaSkpd.objects.filter(pk=row.pk).update(kepala_pegawai_id=pid)
                    upd += 1
            self.stdout.write(f"ASDA_SKPD updated: {upd}")

        self.stdout.write(self.style.SUCCESS("Done."))
