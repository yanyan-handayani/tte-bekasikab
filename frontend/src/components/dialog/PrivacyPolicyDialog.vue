<script setup>
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import { nextTick, onMounted, ref } from 'vue'

const props = defineProps({
    visible: Boolean,
    loading: Boolean
})

const emit = defineEmits(['update:visible', 'accepted'])


const agreed = ref(false)
const loading = ref(false)
const scrollBox = ref(null)
const hasScrolledToBottom = ref(false)

const handleScroll = () => {
    const el = scrollBox.value
    if (!el) return

    const threshold = 5
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - threshold) {
        hasScrolledToBottom.value = true
    }
}

const acceptPolicy = () => {
    if (!agreed.value || !hasScrolledToBottom.value) return

    emit('accepted')
    emit('update:visible', false)
}

onMounted(() => {
    nextTick(() => {
        if (scrollBox.value) {
            scrollBox.value.addEventListener('scroll', handleScroll)
        }
    })
})
</script>

<template>
    <Dialog
        :visible="visible"
        modal
        header="Kebijakan Privasi"
        :closable="false"
        :dismissableMask="false"
        :style="{ width: '50vw' }"
        :breakpoints="{
            '960px': '75vw',
            '640px': '95vw'
        }"
        @update:visible="val => emit('update:visible', val)"
    >
        <div
            ref="scrollBox"            
            @scroll="handleScroll"
            style="max-height: 400px; overflow-y: auto; padding-right: 10px;"
        >
            <div class="policy-box">
                <div class="subtitle">
                    Website Sistem Tanda Tangan Elektronik Kabupaten Bekasi<br>
                    <a href="https://tte.bekasikab.go.id" target="_blank">
                        https://tte.bekasikab.go.id
                    </a>
                </div>

                <h5>1. Pendahuluan</h5>
                <p>
                    Website Sistem Tanda Tangan Elektronik (TTE) Kabupaten Bekasi dikelola oleh
                    Bidang Persandian Dinas Komunikasi Informatika Persandian dan Statistik
                    Pemerintah Kabupaten Bekasi sebagai bagian dari penyelenggaraan layanan
                    pemerintahan berbasis elektronik.
                </p>

                <p>
                    Kebijakan Privasi ini menjelaskan bagaimana kami mengumpulkan, menggunakan,
                    menyimpan, dan melindungi data pribadi pengguna dalam penggunaan layanan TTE.
                </p>

                <h5>2. Dasar Hukum</h5>
                <ul>
                    <li>UU No. 27 Tahun 2022 tentang Perlindungan Data Pribadi</li>
                    <li>UU No. 11 Tahun 2008 tentang ITE</li>
                    <li>Perpres No. 95 Tahun 2018 tentang SPBE</li>
                </ul>

                <h5>3. Informasi yang Dikumpulkan</h5>
                <p>Kami dapat mengumpulkan data sebagai berikut:</p>
                <ul>
                    <li>Nama lengkap</li>
                    <li>NIK / NIP</li>
                    <li>Email resmi instansi</li>
                    <li>Nomor telepon</li>
                    <li>Jabatan dan unit kerja</li>
                    <li>Alamat IP dan log aktivitas sistem</li>
                    <li>Dokumen elektronik dan metadata tanda tangan</li>
                </ul>

                <h5>4. Tujuan Penggunaan Data</h5>
                <ul>
                    <li>Autentikasi dan otorisasi pengguna</li>
                    <li>Penyelenggaraan layanan tanda tangan elektronik</li>
                    <li>Verifikasi keabsahan dokumen</li>
                    <li>Pencatatan audit dan keamanan sistem</li>
                    <li>Pemenuhan kewajiban hukum dan administrasi</li>
                </ul>

                <h5>5. Penyimpanan dan Keamanan Data</h5>
                <p>
                    Kami menerapkan pengamanan teknis dan organisasi yang memadai, termasuk enkripsi data,
                    pembatasan akses berbasis peran, serta audit log sistem.
                </p>

                <h5>6. Pengungkapan Data</h5>
                <p>
                    Data pribadi pengguna tidak akan dibagikan kepada pihak ketiga, kecuali:
                </p>
                <ul>
                    <li>Diperlukan oleh peraturan perundang-undangan</li>
                    <li>Untuk kepentingan penegakan hukum</li>
                    <li>Bekerja sama dengan Penyelenggara Sertifikasi Elektronik resmi</li>
                    <li>Atas persetujuan eksplisit pengguna</li>
                </ul>

                <h5>7. Hak Pengguna</h5>
                <p>Pengguna berhak untuk:</p>
                <ul>
                    <li>Mengakses data pribadinya</li>
                    <li>Memperbaiki atau memperbarui data</li>
                    <li>Mengajukan pengaduan terkait perlindungan data pribadi</li>
                </ul>

                <h5>8. Cookie</h5>
                <p>
                    Website ini menggunakan cookie untuk menjaga sesi login dan meningkatkan keamanan layanan.
                    Pengguna dapat mengatur cookie melalui pengaturan browser.
                </p>

                <h5>9. Perubahan Kebijakan</h5>
                <p>
                    Kebijakan Privasi ini dapat diperbarui sewaktu-waktu dan akan diumumkan melalui website ini.
                </p>

                <h5>10. Kontak</h5>
                <p>
                    Jika terdapat pertanyaan atau pengaduan terkait Kebijakan Privasi ini, silakan hubungi:
                </p>
                <p>
                    <strong>Pengelola Layanan Sistem Tanda Tangan Elektronik</strong><br>
                    Bidang Persandian Dinas Komunikasi Informatika Persandian dan Statistik Pemerintah Kabupaten Bekasi<br>
                    Komp. Perkantoran PEMKAB Bekasi,<br>
                    Sukamahi, Cikarang Pusat,<br>
                    Kabupaten Bekasi, Jawa Barat
                </p>
            </div>
        </div>

        <div class="flex align-items-center mt-4">
            <Checkbox v-model="agreed" binary />
            <label class="ml-2">
                Saya telah membaca dan menyetujui Kebijakan Privasi
            </label>
        </div>

        <div class="flex justify-content-end mt-4">
            <Button
                label="Setuju"
                :disabled="!agreed || !hasScrolledToBottom"
                :loading="loading"
                :disable="loading"
                @click="acceptPolicy"
            />
        </div>
    </Dialog>
</template>

<style scoped>
.policy-box h1 {
    font-size: 22px;
    margin-bottom: 10px;
}
.policy-box h5 {
    margin-top: 20px;
}
.policy-box ul {
    padding-left: 20px;
}
.subtitle {
    margin-bottom: 15px;
    font-size: 14px;
}
</style>