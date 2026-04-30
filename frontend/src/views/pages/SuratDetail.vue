<script setup>
import SuratTahapan from '@/components/dialog/SuratTahapan.vue'
import { useAuthStore } from '@/store/auth'
import { UseSuratStore } from '@/store/surat'
import { formatDateId, formatDateTimeId } from '@/utils/func'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const toast=useToast()
const route = useRoute()
const router = useRouter()
const suratStore = UseSuratStore()
const authStore = useAuthStore()
const actionSelected = ref(null)
const pendingMessage = ref('')

const idSurat = route.params.id

onMounted(async () => {
  try {
      await suratStore.fetchSuratById(idSurat);
      await authStore.me();
  } catch (err) {
      if (err.response && err.response.status === 404) {
          router.push({ name: 'notfound' });
      }
  }
})

const surat = computed(() => suratStore.detail[idSurat] || null)

const tahapanStepper = computed(() => {
  return (
    surat.value?.tahapan
      ?.slice()
      ?.sort((a, b) => a.seq_tahapan - b.seq_tahapan)
    || []
  )
})
const activeStep = computed(() => {
  // Last step
  const idx = tahapanStepper.value
    .map((t, i) => ({ t, i }))
    .filter(x => x.t.sign_status_display?.id_status === 2)
    .pop()

  return idx ? String(idx.i + 1) : ''
})

const activeTahapan = computed(() => {
  // Now step
  if (!tahapanStepper.value.length) return null

  return (
    tahapanStepper.value.find(
      t => t.sign_status_display?.id_status !== 2 && t.sign_status_display?.id_status !== 3
    ) || null
  )
})

const isMyActiveTahapan = computed(() => {
  // Validate is my step?
  if (!activeTahapan.value) return false
  const myPegawaiId = authStore.user?.pegawai?.id
  if (!myPegawaiId) return false

  return (
    activeTahapan.value.pejabat === myPegawaiId
  )
})

watch(activeTahapan, () => {
  actionSelected.value = null
  pendingMessage.value = ''
})

const submitAksi = async ({ id_tahapan, action, message, passphrase }) => {
  try {
    if (action === 'paraf') {
      await suratStore.parafSurat(id_tahapan)
    }
    else if (action === 'sign') {
      await suratStore.signSurat(id_tahapan, passphrase)
    }
    else if (action === 'pending') {
      await suratStore.pendingTahapan(id_tahapan, message)
    }

    toast.add({
      severity: 'success',
      summary: 'Berhasil',
      detail: `Proses ${action} berhasil`,
      life: 10000
    })

    await suratStore.fetchSuratById(idSurat)

  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Gagal',
      detail: e?.response?.data?.detail || e.message,
      life: 6000
    })
  }
}
</script>

<template>
  <div class="p-3">
    <Fluid class="grid grid-cols-12 gap-8">
        <div class="col-span-12 xl:col-span-12">
            
            <div class="card">
                <div class="font-semibold text-xl mb-4">Detail Surat</div>
                <Skeleton v-if="!surat" height="10rem" />
                <template v-else>
                  <div class="flex flex-wrap gap-4">
                  <div class="flex flex-col grow basis-0 gap-2">
                      <label class="font-bold">Tanggal Surat</label>
                      <InputText
                      :value="formatDateId(surat.create_date)"
                      :manualInput="false"
                      />
                  </div>

                  <div class="flex flex-col grow basis-0 gap-2">
                      <label class="font-bold">Nomor Surat</label>
                      <InputText
                      :value="surat.nomor_surat"
                      readonly
                      />
                  </div>
                  </div>

                  <div class="mt-4">
                  <label class="font-bold">Perihal Surat</label>
                  <InputText :value="surat.judul_surat" readonly />
                  </div>

                  <div class="mt-4">
                  <label class="font-bold">Tujuan Surat</label>
                  <InputText :value="surat.tujuan_surat" readonly />
                  </div>

                  <div class="mt-4">
                  <label class="font-bold">Instansi</label>
                  <InputText :value="surat.instansi_nama" readonly />
                  </div>
                  <!-- activeTahapan: {{ activeTahapan }} -->
                  <br />
                  <!-- isMyActiveTahapan: {{ isMyActiveTahapan }} -->
                  <br />
                  <!-- myPegawaiId: {{ authStore.user?.pegawai?.id }} -->
                  <div v-if="activeTahapan && isMyActiveTahapan" class="mt-4">
                    <SuratTahapan
                      :tahapan="activeTahapan"
                      :loading="suratStore.loading"
                      @submit="submitAksi"
                    />                      
                  </div>
                </template>
            </div>

        </div>
        <div class="col-span-12 xl:col-span-6">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Surat</div>
                <Skeleton v-if="!surat" height="10rem" />
                <div v-else>
                  <iframe
                    v-if="surat.file_surat"
                    :src="surat.file_surat"
                    class="w-full border rounded"
                    style="height: 70vh"
                  ></iframe>
                  <div v-else class="text-gray-500 text-sm">
                    File surat tidak tersedia
                  </div>
                </div>
            </div>
        </div>
        <div class="col-span-12 xl:col-span-6">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Surat Telah Ditandatangani</div>
                <Skeleton v-if="!surat" height="10rem" />
                <div v-else>
                  <iframe
                    v-if="surat.file_signed_url"
                    :src="surat.file_signed_url"
                    class="w-full border rounded"
                    style="height: 70vh"
                  ></iframe>
                  <div v-else class="text-gray-500 text-sm">
                    File surat belum tersedia
                  </div>
                </div>
            </div>
        </div>
        <div class="col-span-12 xl:col-span-12">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Timeline Surat</div>
                <Skeleton v-if="!surat" height="10rem" />
                <Stepper :value="activeStep" class="basis-[50rem]" pointer-events-none select-none>
                    <StepList>
                        <Step
                            v-for="(item, index) in tahapanStepper"
                            :key="item.id_tahapan"
                            :value="String(index + 1)"
                            disabled
                            :class="{
                                'font-semibold text-black': String(index + 1) === activeStep,
                                'text-black': String(index + 1) !== activeStep
                            }"
                            >
                            {{ item.pejabat_nama }}
                        </Step>
                    </StepList>
                </Stepper>
                <DataTable
                  :value="tahapanStepper"
                  size="small"
                >
                  <Column field="pejabat_nama" header="Nama" />
                  <Column field="pejabat_jabatan" header="Jabatan" />
                  <Column field="keterangan" header="Keterangan">
                    <template #body="slotProps">
                      <span>{{ slotProps.data.sign_type_display.nama }}</span>
                      <span v-if="slotProps.data.sign_status_display.nama"> - {{ slotProps.data.sign_status_display.nama }}</span>
                      <span v-if="slotProps.data.sign_date">, {{ formatDateTimeId(slotProps.data.sign_date) }} <span v-if="slotProps.data.sign_type_display.id"> </span></span>
                    </template>
                  </Column>
                </DataTable>    
            </div>
        </div>
    </Fluid>
  </div>
</template>