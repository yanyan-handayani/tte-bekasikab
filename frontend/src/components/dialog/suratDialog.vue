<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  modelValue: Object,
  pegawaiOptions: {
    type: Array,
    default: () => []
  },
  loading: Boolean,
  suratTemplate: {
    type: Array,
    default: () => []
  }
})
const emit = defineEmits(['update:visible', 'save'])

const defaultForm = () => ({
  tanggalSurat: null,
  nomorSurat: '',
  judulSurat: '',
  tujuanSurat: '',
  templateRef: null,
  diverifikasi: [],
  ditandatangani: [],
  fileSurat: null
})
const form = ref({})
const submitted = ref(false)
const fileUpload = ref(null)

function onFileSelect(event) {
    if (!event.files || event.files.length === 0) {
        return
    }
    const file = event.files[0]

    form.value.fileSurat = file

    fileUpload.value.clear()
    fileUpload.value.files = [file]
}

function onFileClear() {
  form.value.fileSurat = null
}

watch(
    () => props.modelValue,
    (val) => {
        form.value = { ...defaultForm(), ...(val || {}) }
        submitted.value = false
    },
    { immediate: true }
)

watch(
  () => props.visible,
  (val) => {
    if (val && !props.modelValue) {
      form.value = defaultForm()
      submitted.value = false
      fileUpload.value?.clear()
    }
  }
)

function close() {
    emit('update:visible', false)
}

function save() {
  submitted.value = true
  if (!form.value.nomorSurat) return
  emit('save', form.value)
}

</script>

<template>
    <Dialog
        :visible="visible"
        header="Tambah Surat"
        modal
        @update:visible="emit('update:visible', $event)"
        style="width:950px"
    >
    <div class="grid">
        <div class="col-6 md:col-6">
            <div class="flex flex-col gap-4">
                <div class="flex flex-wrap gap-4">
                    <div class="flex flex-col grow basis-0 gap-2">
                        <label class="block font-bold mb-2">Tanggal Surat</label>
                        <DatePicker
                        v-model="form.tanggalSurat"
                        fluid
                        :invalid="submitted && !form.tanggalSurat"
                        />
                        <small v-if="submitted && !form.tanggalSurat" class="text-red-500">
                        Tanggal wajib diisi
                        </small>
                    </div>
                    <div class="flex flex-col grow basis-0 gap-2">
                        <label class="block font-bold mb-2">Nomor Surat</label>
                        <InputText
                        v-model="form.nomorSurat"
                        fluid
                        :invalid="submitted && !form.nomorSurat"
                        />
                        <small v-if="submitted && !form.nomorSurat" class="text-red-500">
                        Nomor surat wajib diisi
                        </small>
                    </div>
                </div>
                <div>
                    <label class="block font-bold mb-2">Perihal Surat</label>
                    <InputText v-model="form.judulSurat" fluid />
                </div>

                <div>
                    <label class="block font-bold mb-2">Tujuan Surat</label>
                    <InputText v-model="form.tujuanSurat" fluid />
                </div>

                <div>
                    <label class="block font-bold mb-2">Jenis Surat/Dokumen</label>
                    <Select
                        v-model="form.templateRef"
                        :options="suratTemplate"
                        optionLabel="nama"
                        optionValue="id_template"
                        placeholder="Pilih Jenis Surat/Dokumen"
                        fluid
                        showClear
                    />  
                </div>

                <div>
                    <label class="block font-bold mb-2">Unggah File (PDF)</label>
                    <FileUpload
                        ref="fileUpload" name="fileSurat" accept="application/pdf" :maxFileSize="2097152" customUpload :multiple="false" :showUploadButton="false" :showCancelButton="false" @select="onFileSelect" @remove="onFileClear" :class="{ 'p-invalid': submitted && !form.  fileSurat }">
                        <template #empty>
                            <div class="flex flex-col items-center justify-center p-4 text-gray-500">
                            <i class="pi pi-cloud-upload text-3xl mb-2" />
                            <span>Drag & drop PDF di sini</span>
                            <small>Maks. 2 MB</small>
                            </div>
                        </template>
                        <template #content>
                        </template>
                    </FileUpload>
                    <small v-if="submitted && !form.fileSurat" class="text-red-500">
                        File surat wajib diupload!
                    </small>
                </div>
            </div>

            <div class="col-6 md:col-6">
                <div class="flex flex-col gap-4">
                    <div>
                        <label class="block font-bold mb-2">Diverifikasi Oleh</label>
                        <MultiSelect
                        v-model="form.diverifikasi"
                        :options="props.pegawaiOptions"
                        optionLabel="nama"
                        optionValue="id"
                        placeholder="Pilih"
                        display="chip"
                        filter
                        fluid
                        :invalid="submitted && (!form.diverifikasi || form.diverifikasi.length === 0)"
                            />
                        <small v-if="submitted && (!form.diverifikasi || form.diverifikasi.length === 0)" class="text-red-500">
                        Minimal pilih 1 verifikator dalam verifikasi
                        </small>
                    </div>
                    <div>
                        <label class="block font-bold mb-2">Ditandatangani Oleh</label>
                        <MultiSelect
                        v-model="form.ditandatangani"
                        :options="props.pegawaiOptions"
                        optionLabel="nama"
                        optionValue="id"
                        placeholder="Pilih"
                        display="chip"
                        filter
                        fluid
                        :invalid="submitted && (!form.ditandatangani || form.ditandatangani.length === 0)"
                        />
                        <small v-if="submitted && (!form.ditandatangani || form.ditandatangani.length === 0)" class="text-red-500">
                        Minimal pilih 1 penandatangan
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <template #footer>
      <Button label="Batal" text @click="close" />
      <Button label="Simpan" :loading="props.loading" icon="pi pi-check" @click="save" />
    </template>
  </Dialog>
</template>
<style scoped>
:deep(.p-multiselect) {
    width: 100% !important;
    max-width: 100% !important;
}

:deep(.p-multiselect-label-container) {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0.25rem;
}

:deep(.p-multiselect-label) {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0.25rem;
    max-height: 80px;
    overflow-y: auto;
}

:deep(.p-multiselect-token) {
    max-width: 100%;
    white-space: normal !important;
    word-break: break-word;
}
</style>