<script setup>
import PrivacyPolicyDialog from '@/components/dialog/PrivacyPolicyDialog.vue';
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import { useAuthStore } from '@/store/auth';
import { InputOtp } from 'primevue';
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const otp = ref('')
const captchaText = ref('')
const captchaInput = ref('')
const captchaCanvas = ref(null)
const showPrivacyDialog = ref(false)
const submitLogin = ref(false)

const randomText = (length = 5) => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return Array.from({ length }, () =>
        chars.charAt(Math.floor(Math.random() * chars.length))
    ).join('')
}
onMounted(() => {
    drawCaptcha()
})
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

const  login = async () => {
    if (captchaInput.value.toUpperCase() !== captchaText.value) {
        auth.error = 'Captcha salah'
        drawCaptcha()
        captchaInput.value = ''
        return
    }
    try{
        submitLogin.value = true
        await auth.login(username.value, password.value)
        if (auth.step !== 'otp') {
            showPrivacyDialog.value = true
        }
        // router.push('/')
    } catch (err) {
        captchaInput.value = ''
        drawCaptcha()
        submitLogin.value = false
    }
}

const verifyOtp = async () => {
    if (!otp.value || otp.value.length !== 6) return
    try {
        await auth.verifyOtp(otp.value)
        showPrivacyDialog.value = true
        submitLogin.value = true
        // router.push('/')
        // auth.$reset()
    } catch (err) {
        auth.err = null
        otp.value = ''
        submitLogin.value = false
    }
}

const handlePrivacyAccepted = async () => {
    const params = {
        'kategori': 1,
        'aktivitas': 'LOGIN_SUCCESS'
    }
    const targetPath = route.query.redirect || '/'
    await auth.privacyLog(params)
    router.push(targetPath)    
    auth.$reset()
}
</script>

<template>
    <FloatingConfigurator />
    <div
        class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen w-full overflow-x-hidden"
    >
        <div class="flex flex-col items-center justify-center w-full" style="max-width: 60vh;">
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
                        <div class="flex justify-center items-center mb-4">
                            <Image src="/fileassets/bsre.png" style="width: 30%;" preview />
                        </div>
                        <span
                            class="text-muted-color font-medium"
                            v-if="auth.step === 'credential'"
                        >
                            Silahkan Login
                        </span>
                        <span
                            class="text-muted-color font-medium"
                            v-if="auth.step === 'otp'"
                        >
                            Verifikasi 2FA akun anda aktif
                        </span>
                    </div>

                    <div v-show="auth.step === 'credential'">
                        <label class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2">
                            Username
                        </label>
                        <InputText
                            v-model="username"
                            placeholder="Username / NIP"
                            class="w-full mb-6"
                        />

                        <label class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2">
                            Password
                        </label>
                        <Password
                            v-model="password"
                            placeholder="Password"
                            toggleMask
                            class="mb-4"
                            fluid
                            :feedback="false"
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
                        <div class="flex justify-end mt-4">
                            <Button
                                label="Lupa Password?"
                                class="p-button-text p-button-plain mr-auto"
                                @click="$router.push('/auth/forgot-password')"
                                :disabled="submitLogin"
                            />
                            <Button
                            label="Sign In"
                            :loading="auth.loading"
                            :disabled="!captchaInput || !username || !password || auth.loading || submitLogin"
                            @click="login"
                            />
                        </div>
                    </div>
                    <div v-if="auth.step === 'otp'">
                        <div class="flex flex-col items-center justify-center mb-4">
                            <label for="otp" class="mb-3">Masukkan Kode OTP</label>
                            <InputOtp v-model="otp" :length="6" integerOnly autoFocus />
                            <Button
                                label="Verifikasi"
                                class="mt-4"
                                :loading="auth.loading"
                                :disabled="!otp || otp.length !== 6 || auth.loading || submitLogin"
                                @click="verifyOtp"
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
        <PrivacyPolicyDialog
            v-model:visible="showPrivacyDialog"
            :loading="auth.loadingL"
            @accepted="handlePrivacyAccepted"
        />
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
