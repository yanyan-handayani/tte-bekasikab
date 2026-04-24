<script setup>
import { useAuthStore } from '@/store/auth'
import { useToast } from 'primevue/usetoast'
import { ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  mode: {
    type: String,
    default: 'enable'
  }
})

const emit = defineEmits(['update:visible', 'verified'])

const auth = useAuthStore()
const toast = useToast()

const otp = ref('')

watch(
  () => props.visible,
  (val) => {
    if (!val) otp.value = ''
  }
)

async function verifyold() {
  try {
    const otpClean = String(otp.value).trim()

    if (!/^\d{6}$/.test(otpClean)) {
      throw new Error('OTP tidak valid')
    }

    await auth.enable2FA({
      otp: otpClean 
    })

    toast.add({
      severity: 'success',
      summary: '2FA Aktif'
    })
    emit('verified')
    emit('update:visible', false)
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 
      e.message || e.detail || 'Terjadi kesalahan',
      life: 12000
    })
  }
}
async function verify() {
  try {
    const otpClean = String(otp.value).trim()

    if (!/^\d{6}$/.test(otpClean)) {
      throw new Error('OTP harus 6 digit angka')
    }

    if (props.mode === 'enable') {
      await auth.enable2FA({ otp: otpClean })

      toast.add({
        severity: 'success',
        summary: '2FA Berhasil Diaktifkan',
        life: 12000
      })
    } else {
      const params = {
        otp: otpClean
      }
      await auth.disable2FA(params)

      toast.add({
        severity: 'success',
        summary: '2FA Berhasil Dinonaktifkan',
        life: 12000
      })
    }

    emit('verified')
    emit('update:visible', false)

  } catch (e) {
    toast.add({
      severity: 'error',
      summary: e?.response?.data?.detail || e.message || 'Terjadi kesalahan',
      life: 12000
    })
    otp.value = ''
  }
}

function close() {
  emit('update:visible', false)
}
</script>
<template>
    <Dialog
    :visible="visible"
    :header="props.mode === 'enable' ? 'Aktifkan 2FA' : 'Nonaktifkan 2FA'"
    modal
    style="width:400px"
    @update:visible="emit('update:visible', $event)"
    >
    <div class="flex flex-col gap-4 items-center">
        <img
        v-if="props.mode === 'enable' && auth.qr"
        :src="auth.qr"
        alt="QR 2FA"
        class="w-48"
        />
        <label for="otp">Masukkan Kode OTP</label>
        <InputOtp v-model="otp" :length="6" integerOnly />
    </div>

    <template #footer>
        <Button label="Batal" text @click="close" />
        <Button :loading="auth.loading" label="Verifikasi" @click="verify" />
    </template>
    </Dialog>

</template>