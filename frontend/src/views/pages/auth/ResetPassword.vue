<script setup>
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import { useAuthStore } from '@/store/auth';
import { useToast } from 'primevue/usetoast';
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const toast = useToast();

const password = ref('')
const email = ref('')
const token = ref('')
const captchaText = ref('')
const captchaInput = ref('')
const uid = ref('')
const confirmPassword = ref('')
const submitted = ref(false)

onMounted(() => {
    uid.value = route.query.uid
    token.value = route.query.token

    if (!uid.value || !token.value) {
        router.push('/auth/login')
    }
})


const resetPassword = async () => {
    try {
        const params={
            new_password: password.value,
            uid: uid.value,
            token: token.value,
        }
        await auth.resetPassword(params)
        toast.add({severity: 'success', summary: 'Berhasil', detail: 'Password berhasil diganti, silakan login.', life: 12000})
        router.push('/auth/login')
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Gagal', detail: auth.error || 'Gagal mengganti password!', life: 12000 })
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
    router.push('/auth/forgot-password')
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
                    </div>

                    <div>
                        <p class="mb-4 text-center">
                            Silahkan buat Password baru Anda.
                        </p>
        
                        <label class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2">
                            Password Baru
                        </label>
                        <Password
                            v-model="password"
                            placeholder="Password"
                            toggleMask
                            class="mb-4"
                            fluid
                            :feedback="false"
                        />
                        <div class="flex justify-between mt-4">
                            <Button
                                label="Kembali"
                                text
                                severity="secondary"
                                @click="backToRequest"
                            />

                            <Button
                                label="Reset Password"
                                :loading="auth.loading"
                                @click="resetPassword"
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
