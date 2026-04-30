<script setup>
import { useLaporanStore } from '@/store/laporan';
import { useMasterStore } from '@/store/master';
import { useTransaksiStore } from '@/store/transaksi';
import { FilterMatchMode } from '@primevue/core/api';
import { useToast } from 'primevue/usetoast';
import { computed, onMounted, ref } from 'vue';


const trx = useTransaksiStore();
const master = useMasterStore();
const beritaAcaraStore = useLaporanStore();

onMounted(() => {
    trx.loadTransaksi();
    master.loadKegiatan();
    master.loadRekening();
    master.loadBarang();
    master.loadPegawai();
    beritaAcaraStore.listBeritaAcara();
    });

const toast = useToast();
const dt = ref();
const selectedProducts = ref();
const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS }
});

const beritaTable = computed(() => {
    const list = beritaAcaraStore.beritaAcara?.data ?? [];
    return list.map(item => {
        const nip= item.nip || "" ;
        const nama= item.nama || "" ;
        const pic = nip + " " + nama;
        return {
            id: item.id,
            tanggal: item.tanggal || "-",  
            pic: pic,
            subUnit: item.sub_unit || "-",
            jenisTransaksi: item.status || "-",
        };
    });
});

function exportCSV() {
    dt.value.exportCSV();
}

function getStatusLabel(status) {
    switch (status) {
        case 'Barang Masuk':
            return 'success';

        case 'Barang Keluar':
            return 'danger';

        default:
            return null;
    }
}
const downloadBast = async (headId) => {
    const res = await beritaAcaraStore.bastGenerate(headId);

    const blob = new Blob([res.data], { type: "application/pdf" });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `BAST-${headId}.pdf`;
    a.click();

    window.URL.revokeObjectURL(url);
};


</script>

<template>
    <div>
        <div class="card">
                
            <DataTable
                ref="dt"
                v-model:selection="selectedProducts"
                :value="beritaTable"
                dataKey="id"
                :paginator="true"
                :rows="10"
                :filters="filters"
                paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
                :rowsPerPageOptions="[5, 10, 25]"
                currentPageReportTemplate="Showing {first} to {last} of {totalRecords} data"
            >
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Berita Acara</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="filters['global'].value" placeholder="Search..." />
                        </IconField>
                    </div>
                </template>
                <Column selectionMode="multiple" style="width: 3rem" :exportable="false"></Column>
                <Column field="tanggal" header="Tanggal" sortable style="min-width: 8rem"></Column>
                <Column field="subUnit" header="Sub Unit" sortable style="min-width: 8rem"></Column>
                <Column field="pic" header="PIC" sortable style="min-width: 8rem"></Column>
                <Column field="jenisTransaksi" header="Jenis Transaksi" sortable style="min-width: 8rem">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.jenisTransaksi" :severity="getStatusLabel(slotProps.data.jenisTransaksi)" />
                    </template>
                </Column>
                <Column field="id" :exportable="false" style="min-width: 8rem">
                    <template #body="slotProps">
                        <!-- <a 
                            :href="`/as/ba.pdf`" 
                            target="_blank"
                            class="p-button p-button-outlined p-button-rounded mr-2 flex items-center justify-center"
                            style="width: 2.5rem; height: 2.5rem;"
                        >
                            <i class="pi pi-file-pdf"></i>
                        </a> -->
                        <Button
                        label="Unduh BAST"
                        icon="pi pi-file-pdf"
                        severity="primary"
                        @click="downloadBast(slotProps.data.id)"
                        />
                    </template>


                </Column>
            </DataTable>
        </div>
    </div>
</template>


<style>
.p-select-overlay {
    /* background: yellow !important; */
    min-width: unset !important;      
    width: var(--trigger-width) !important; 
    /* max-width: var(--trigger-width) !important; */
    max-width: 360px !important;

    max-height: 18rem !important;     
    overflow-y: auto !important;
    overflow-x: hidden !important;
}

.p-select {
    width: 100%;
    --trigger-width: 100%;
}
.p-select-option {
    white-space: normal !important;
    line-height: 1.3;
    padding: 8px 10px !important;
}

.p-select-option .item-code {
    font-weight: 700;
    font-size: 0.9rem;
}

.p-select-option .item-name {
    font-size: 0.8rem;
    opacity: 0.75;
}

</style>
