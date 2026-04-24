<script setup>
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import { useAuthStore } from '@/store/auth';
import { useToast } from 'primevue/usetoast';
import { onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

const auth = useAuthStore()
const router = useRouter()
const toast = useToast();

const username = ref('')
const password = ref('')
const otp = ref('')
const email = ref('')
const token = ref('')
const captchaText = ref('')
const captchaInput = ref('')
const captchaCanvas = ref(null)

const randomText = (length = 5) => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return Array.from({ length }, () =>
        chars.charAt(Math.floor(Math.random() * chars.length))
    ).join('')
}

const drawCaptcha = () => {
    const canvas = captchaCanvas.value
    const ctx = canvas.getContext('2d')

    captchaText.value = randomText()

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#f2f2f2'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    let x = 15
    for (const char of captchaText.value) {
        ctx.save()
        ctx.font = '24px Arial'
        ctx.fillStyle = '#222'
        ctx.filter = `blur(0.9px)`
        ctx.translate(x, 32)
        ctx.rotate((Math.random() - 0.5) * 0.5)
        ctx.fillText(char, 0, 0)
        ctx.restore()
        x += 18
    }

    for (let i = 0; i < 20; i++) {
        ctx.strokeStyle = 'rgba(0,0,0,0.4)'
        ctx.lineWidth = Math.random() * 1.5 + 1
        ctx.beginPath()
        ctx.moveTo(Math.random() * 120, Math.random() * 50)
        ctx.lineTo(Math.random() * 120, Math.random() * 50)
        ctx.stroke()
    }
}

onMounted(() => {
    drawCaptcha()
})

const  forgotPassword = async () => {
    if (captchaInput.value.toUpperCase() !== captchaText.value) {
        auth.error = 'Captcha salah'
        drawCaptcha()
        captchaInput.value = ''
        return
    }
    try {
        const params = {
            email: email.value,
        }

        await auth.forgotPassword(params)

        drawCaptcha()
        captchaInput.value = ''
        email.value = ''

        toast.add({
            severity: 'success',
            summary: 'Berhasil',
            detail: 'Email berhasil dikirim, periksa email anda.',
            life: 12000
        })
    } catch (err) {
        toast.add({
            severity: 'error',
            summary: 'Gagal',
            detail: auth.error,
            life: 6000
        })
    }
}

watch(
    () => auth.isAuthenticated,
    (val) => {
        if (val === true) {
            router.push('/')
        }
    }
)
const backToRequest = () => {
    router.push('/auth/login')
}   
</script>

<template>
    <FloatingConfigurator />
    <div
        class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden"
    >
        <div class="flex flex-col items-center justify-center">
            <div
                style="border-radius: 16px; padding: 0.3rem;"
            >
                <div
                    class="w-full bg-surface-0 dark:bg-surface-900 py-20 px-8 sm:px-5"
                    style="border-radius: 13px"
                >

                    <div class="text-center mb-8">
                        <div class="text-surface-900 dark:text-surface-0 text-3xl font-medium mb-4">
                            Sistem Aplikasi Tanda Tangan Elektronik
                        </div>
                        <div class="text-surface-900 dark:text-surface-0 text-2xl font-medium mb-4">
                            Kabupaten Bekasi
                        </div>
                        <div class="text-surface-900 dark:text-surface-0 text-1xl font-medium mb-4">
                            Lupa Password
                        </div>
                        <span   
                            class="text-muted-color font-medium"
                        >
                            Silahkan Masukan Email Anda
                        </span>
                    </div>

                    <div >
                        <label class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2">
                            Email
                        </label>
                        <InputText
                            v-model="email"
                            placeholder="Email"
                            class="w-full mb-6"
                        />
                        <div class="mb-4">
                            <div class="flex items-center gap-3 mb-2">
                                <canvas
                                    ref="captchaCanvas"
                                    width="120"
                                    height="50"
                                    class="border rounded"
                                ></canvas>

                                <Button
                                    icon="pi pi-refresh"
                                    text
                                    rounded
                                    @click="drawCaptcha"
                                />
                            </div>

                            <InputText
                                v-model="captchaInput"
                                placeholder="Masukkan captcha"
                                class="w-full"
                            />
                        </div>
                        <div class="flex justify-between mt-4">
                            <Button
                                label="Kembali"
                                text
                                severity="secondary"
                                @click="backToRequest"
                            />

                            <Button
                                label="Kirim"
                                :loading="auth.loading"
                                @click="forgotPassword"
                            />
                        </div>
                    </div>

                    
                    <Message
                        severity="error"
                        v-if="auth.error"
                        class="mt-4"
                    >
                        {{ auth.error }}
                    </Message>

                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.pi-eye {
    transform: scale(1.6);
    margin-right: 1rem;
}

.pi-eye-slash {
    transform: scale(1.6);
    margin-right: 1rem;
}
</style>
