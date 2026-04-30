<script setup>
import { useToast } from 'primevue/usetoast';
import { computed, onMounted, ref, watch } from 'vue';

import suratDialog from '@/components/dialog/suratDialog.vue';
import { useAuthStore } from '@/store/auth';
import { UseSuratStore } from '@/store/surat';
import { debounce, formatDateId, formatDateTimeId } from '@/utils/func';

const auth = useAuthStore()
const surat = UseSuratStore();

onMounted(() => {
    loadData()
    surat.suratTemplateList();
});

const toast = useToast();
const dt = ref();
const deleteProductsDialog = ref(false);
const selectedProducts = ref();
const dialogVisible = ref(false)
const selectedSurat = ref(null)
const expandedRows = ref({})
const globalSearch = ref('')
const rows = ref(10)
const page = ref(1)
const first = ref(0)
const product = ref()


const suratList = computed(() => {
    return surat.list || [];
})
const pegawaiOptions = computed(() => {
  if (!auth.user?.pegawai) return []

  const pegawai = auth.user.pegawai

  const selfOption = {
    id: pegawai.id,
    nip: pegawai.nip,
    nama: `${pegawai.nama}`,
    jabatan: pegawai.id_jabatan,
    level:'',
    is_self: true
  }

  const atasanOptions = pegawai.atasan.flatMap(a =>
    a.pejabat.map(p => ({
      id: p.id,
      nip: p.nip,
      nama: `${p.nama} (${a.jabatan.nama_jabatan})`,
      jabatan: a.jabatan.id_jabatan,
      level: a.jabatan.level_jabatan,
      is_self: false
    }))
  )

  const merged = [selfOption, ...atasanOptions]

  return merged.filter(
    (v, i, arr) => arr.findIndex(x => x.id === v.id) === i
  )
})

// const filters = ref({
//     global: { value: null, matchMode: FilterMatchMode.CONTAINS }
// });
const submitted = ref(false);

const statuses = ref([
    { label: 'Selesai', value: '3',severity: 'success' },
    { label: 'Proses', value: '1',severity: 'warning' },
    { label: 'Pending', value: '2' ,severity: 'secondary'}
]);
function getStatusMeta(value) {
    return statuses.value.find(s => s.value == value);
}

function openNew() {
    auth.me()
    selectedSurat.value = null
    dialogVisible.value = true
}

function openEdit(data) {
  selectedSurat.value = { ...data }
  dialogVisible.value = true
}
function buildTahapan(payload) {
    let seq = 0
    const tahapan = [];

    tahapan.push({
        seq: seq++,
        pegawai_id: auth.user.pegawai.id,
        sign_type: 3
    });

    (payload.diverifikasi || []).forEach(id => {
        tahapan.push({
            seq: seq++,
            pegawai_id: id,
            sign_type: 1 
        })
    });

    (payload.ditandatangani || []).forEach(id => {
        tahapan.push({
            seq: seq++,
            pegawai_id: id,
            sign_type: 2
        })
    })

    return tahapan
}

async function handleSave(payload) {
  try {
     if (!payload.diverifikasi || payload.diverifikasi.length === 0) {
      toast.add({ severity: 'warn', summary: 'Validasi', detail: 'Minimal pilih 1 verifikator dalam verifikasi', life: 4000 })
      return
    }

    if (!payload.ditandatangani || payload.ditandatangani.length === 0) {
        toast.add({ severity: 'warn', summary: 'Validasi', detail: 'Minimal pilih 1 penandatangan', life: 4000 })
      return
    }
    if (payload.id) {
        await surat.updateSurat(payload)
        toast.add({ severity: 'success', summary: 'Berhasil', detail: 'Surat diperbarui', life: 6000 })
    } else {
        const fd = new FormData()

        fd.append('nomor_surat', payload.nomorSurat || '000.0/TEST/2026')
        fd.append('judul_surat', payload.judulSurat)
        fd.append('tujuan_surat', payload.tujuanSurat)
        fd.append('instansi_ref', String(auth.user.pegawai.instansi.id))

        fd.append('file_surat', payload.fileSurat)
        if(payload.templateRef){
            fd.append('template_ref', payload.templateRef || null)
        }

        const tahapan = buildTahapan(payload)
        fd.append('tahapan', JSON.stringify(tahapan))

        await surat.createSurat(fd)

        dialogVisible.value = false
        surat.fetchSurat()
        toast.add({ severity: 'success', summary: 'Berhasil', detail: 'Surat ditambahkan', life: 6000 })
    }
    dialogVisible.value = false
    surat.fetchSurat()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Gagal', detail: 'Terjadi kesalahan', life: 6000 })
  }
}

function exportCSV() {
    dt.value.exportCSV();
}

function confirmDeleteSelected(data) {
    product.value = data;
    deleteProductsDialog.value = true;
}

const onPage = (event) => {
    page.value = event.page + 1
    rows.value = event.rows
    first.value = event.first
    loadData()
}

const buildParams = () => {
    const params = {
        page: page.value,
        page_size: rows.value,
    }
    if (globalSearch.value && globalSearch.value.trim() !== '') {
        params.search = globalSearch.value
    }
    return params
}

const loadData = () => {
    surat.fetchSurat(buildParams())
}

watch(
    globalSearch,
    debounce(() => {
        page.value = 1
        first.value = 0
        loadData()
    }, 500)
)

const onRowExpand = async (event) => {
    const headId = event.data.id_surat
    await surat.fetchSuratById(headId)
    
}
const sortedTahapan = (id) => {
  return (
    surat.detail[id]?.tahapan
      ?.slice() 
      ?.sort((a, b) => a.seq_tahapan - b.seq_tahapan)
    || []
  )
}

async function deleteProduct(){
    try {
        await surat.deleteSurat(product.value.id_surat)
        deleteProductsDialog.value = false
        loadData()
        toast.add({ severity: 'success', summary: 'Berhasil', detail: 'Surat dihapus', life: 3000 })
    } catch (e) {
        const err = e.response?.data || e.message
        toast.add({ severity: 'error', summary: 'Gagal', detail: err.detail, life: 6000 })
    }
}
</script>

<template>
    <div>
        <div class="card">
            <Toolbar class="mb-6">
                <template #start>
                    <Button label="New" icon="pi pi-plus" severity="secondary" class="mr-2" @click="openNew" />
                </template>

                <template #end>
                    <Button v-show="false" label="Export" icon="pi pi-upload" severity="secondary" @click="exportCSV($event)" />
                </template>
            </Toolbar>  

            <DataTable
                ref="dt"
                v-model:selection="selectedProducts"
                :value="suratList"
                dataKey="id_surat"
                v-model:expandedRows="expandedRows"
                @rowExpand="onRowExpand"
                lazy
                :first="first"
                :paginator="true"
                :rows="rows"
                :totalRecords="surat.pagination.total"
                @page="onPage"
                paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
                :rowsPerPageOptions="[5, 10, 25]"
                currentPageReportTemplate="Menampilkan {first} s/d {last} dari {totalRecords} data"
            >
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Surat</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="globalSearch" placeholder="Search..." />
                        </IconField>
                    </div>
                </template>

                <!-- <Column selectionMode="multiple" style="width: 3rem" :exportable="false"></Column> --> 
                <Column expander style="width:3rem">
                
                </Column>
                <Column field="create_date"  header="Tanggal" sortable style="min-width: 8rem">
                    <template #body="slotProps">
                        <Skeleton v-if="surat.loadingFs"></Skeleton>
                        <span v-else>{{ formatDateId(slotProps.data.create_date) }}</span>
                    </template>
                </Column>
                <Column  field="nomor_surat"  header="Nomor Surat" sortable style="min-width: 16rem">
                    <template #body="slotProps">
                        <Skeleton v-if="surat.loadingFs"></Skeleton>
                        <span v-else>{{ slotProps.data.nomor_surat }}</span>
                    </template>
                </Column>
                <Column field="judul_surat" header="Perihal Surat" sortable style="min-width: 10rem">
                    <template #body="slotProps">
                        <Skeleton v-if="surat.loadingFs"></Skeleton>
                        <span v-else>{{ slotProps.data.judul_surat }}</span>    
                    </template>
                </Column>
                <Column field="tujuan_surat" header="Tujuan Surat" sortable style="min-width: 10rem">
                    <template #body="slotProps">
                        <Skeleton v-if="surat.loadingFs"></Skeleton>
                        <span v-else>{{ slotProps.data.tujuan_surat }}</span>
                    </template>
                </Column>
                <Column header="Status" sortable style="min-width: 12rem">
                    <template #body="slotProps">
                        <Skeleton v-if="surat.loadingFs"></Skeleton>
                        <Tag v-else
                            :value="getStatusMeta(slotProps.data.is_finish)?.label"
                            :severity="getStatusMeta(slotProps.data.is_finish)?.severity"
                        />
                    </template>
                </Column>
                <Column :exportable="false" style="min-width: 12rem">
                    <template #body="slotProps">
                        <!-- <Button icon="pi pi-pencil" outlined rounded class="mr-2" @click="editProduct(slotProps.data)" /> -->
                        <Button icon="pi pi-trash" outlined rounded class="mr-2" severity="danger" @click="confirmDeleteSelected(slotProps.data)" />
                        <RouterLink
                        :to="{ name: 'surat-detail', params: { id: slotProps.data.id_surat } }"
                        >
                            <Button icon="pi pi-eye" severity="info" outlined rounded :severity="info" class="mr-2"/>
                        </RouterLink>
                    </template>
                </Column>
                <template #expansion="slotProps">
                    <div class="p-3">
                        <DataTable
                            v-if="surat.detail[slotProps.data.id_surat]"
                            :value="sortedTahapan(slotProps.data.id_surat)"
                            size="small"
                        >
                            <template #header>
                                <h5 class="text-md">Timeline Surat</h5>
                            </template>
                            <Column field="pejabat_nama" header="Nama" />
                            <Column field="pejabat_jabatan" header="Jabatan" />
                            <Column field="keterangan" header="Keterangan">
                                <template #body="slotProps">
                                    <span>{{ slotProps.data.sign_type_display.nama }}</span>
                                    <span v-if="slotProps.data.sign_status_display.nama"> - {{ slotProps.data.sign_status_display.nama }}</span>
                                    <span v-if="slotProps.data.sign_date">, {{ formatDateTimeId(slotProps.data.sign_date) }}</span>
                                </template>
                            </Column>
                        </DataTable>
                        <Skeleton
                            v-else
                            height="4rem"
                        />
                    </div>
                </template>
            </DataTable>
        </div>  
        <Dialog v-model:visible="deleteProductsDialog" :style="{ width: '450px' }" header="Confirm" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle !text-3xl" />
                <span v-if="product"
                    >Anda akan menghapus surat dengan Nomor: <b>{{ product.nomor_surat }}</b><template v-if="product.judul_surat"> Perihal: <b>{{ product.judul_surat }}</b></template> 
                    ?</span
                >
            </div>
            <template #footer>
                <Button label="Ya" icon="pi pi-check" text @click="deleteProduct" />
                <Button label="Tidak" icon="pi pi-times" @click="deleteProductsDialog = false" />
            </template>
        </Dialog>
        <suratDialog v-model:visible="dialogVisible" :loading="surat.loading" :modelValue="selectedSurat" :suratTemplate="surat.suratTpl" :pegawai-options="pegawaiOptions" @save="handleSave"    />      
    </div>
</template>
