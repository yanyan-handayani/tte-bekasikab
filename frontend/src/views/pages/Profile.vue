<script setup>
import twofasetupDialog from '@/components/dialog/twofasetupDialog.vue';
import { useAuthStore } from '@/store/auth';
import { useProfileStore } from '@/store/profile';

import { ToggleSwitch } from 'primevue';
import { useToast } from 'primevue/usetoast';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';


const router = useRouter();
const auth = useAuthStore();
const profile= useProfileStore();

onMounted(() => {
    auth.me();
});

const user = computed(() => auth.user);

const pegawai = computed(() => user.value?.pegawai || {});

const toast = useToast();
const show2FADialog = ref(false)
const twofaMode = ref('enable')
const tfa = computed(() => auth.user?.twofa?.enabled ?? false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const submitted = ref(false)
const changePassDialog = ref(false)
const pendingPayload = ref(null)
const ttdFile = ref(null)
const parafFile = ref(null)
const forcePassword = localStorage.getItem('force_change_password') === 'true';
const forcePasswordDialog = ref(forcePassword)
const oldPasswordInput = ref(null)

async function onToggle2FA(val) {
  try {
    if (val) {
      const res = await auth.loadTotpSetup()
      console.log(res.data.type)
      console.log(res.data.size)
      twofaMode.value = 'enable'
      show2FADialog.value = true
    } else {
      twofaMode.value = 'disable'
      show2FADialog.value = true
    }
  } catch(error) {
    console.error(error)
    toast.add({
      severity: 'error',
      summary: 'Gagal',
      detail: 'Operasi 2FA gagal',
      life: 12000
    })
  }
}

const onSelectTTD = (event) => {
    ttdFile.value = event.files[0]
}
const onSelectParaf = (event) => {
    parafFile.value = event.files[0]
}

const specimentUpload = async () => {
    if (!ttdFile.value && !parafFile.value) {
        toast.add({
            severity: 'warn',
            summary: 'Warning',
            detail: 'Minimal satu file harus diupload',
            life: 4000
        })
        return
    }

    const formData = new FormData()
    if (parafFile.value) {
        formData.append('specimen_paraf', parafFile.value)
    }
    if (ttdFile.value) {
        formData.append('specimen_ttd', ttdFile.value)
    }

    try {
        const idp= auth.user.pegawai.id
        await profile.patchSpecimen(idp, formData)
        await auth.me()
        toast.add({
            severity: 'success',
            summary: 'Berhasil',
            detail: 'Spesimen berhasil disimpan',
            life: 4000
        })
    } catch (e) {
        toast.add({
            severity: 'error',
            summary: 'Gagal',
            detail: e?.response?.data?.detail || e.message,
            life: 6000
        })
    }
}

const submitChangePassword = async (confirmed = false) => {
    // if (auth.loading) return 
    changePassDialog.value = false
    if (!confirmed) {
        submitted.value = true
        if (newPassword.value !== confirmPassword.value) {
            toast.add({ severity: 'error', summary: 'Validasi gagal', detail: 'Konfirmasi password tidak sama',life: 6000 })
            return
        }
        pendingPayload.value = {
            old_password: oldPassword.value,
            new_password: newPassword.value,
            new_password_confirm: confirmPassword.value
        }
        changePassDialog.value = true
        return
    }
    try {
        await auth.changePassword(pendingPayload.value)
        toast.add({severity: 'success', summary: 'Berhasil', detail: 'Password berhasil diganti, silakan login ulang', life: 6000})
        changePassDialog.value = false
        await auth.logout()
        router.push('/auth/login')
    } catch (err) {
        toast.add({
            severity: 'error',
            summary: 'Gagal',
            detail: auth.error || 'Gagal mengganti password',
            life: 6000
        })
        auth.error = null
    }
}

</script>

<template>
    <div>
        <Fluid class="flex mt-8">
        <div class="card flex flex-col gap-4 w-full">
            <div class="font-semibold text-xl">Profile</div>
            <div class="flex flex-col md:flex-row gap-4">
                <InputGroup>
                    <InputGroupAddon >
                        <i class="pi pi-user"></i>
                    </InputGroupAddon>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>
                    <InputText v-else  class="w-full" :value="pegawai.nip" disabled />
                </InputGroup>
                <InputGroup>
                    <InputGroupAddon>
                        <i class="pi pi-user"></i>
                    </InputGroupAddon>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>
                    <InputText class="w-full" v-else :value="pegawai.nama" placeholder="Nama" disabled/>
                </InputGroup>
            </div>
            <div class="flex flex-col md:flex-row gap-4">
                <InputGroup>
                    <InputGroupAddon>
                        <i class="pi pi-building"></i>
                    </InputGroupAddon>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>
                    <InputText class="w-full" v-else placeholder="Jabatan" disabled />
                </InputGroup>
                <InputGroup>
                    <InputGroupAddon>
                        <i class="pi pi-building"></i>
                    </InputGroupAddon>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>
                    <InputText class="w-full" v-else :value="pegawai.instansi?.nama" placeholder="Instansi" disabled/>
                </InputGroup>
            </div>
            <div class="font-semibold text-xl">Spesimen</div>
            <div class="flex flex-col md:flex-row gap-4 w-full">
                <div class="flex flex-col w-full gap-2">
                    <label for="name2">TTD</label>
                    <FileUpload mode="basic" accept="image/*" @select="onSelectTTD"/>
                </div>
                <div class="flex flex-col w-full gap-2">
                    <label for="email2">Paraf</label>
                    <FileUpload mode="basic" accept="image/*" @select="onSelectParaf"/>
                </div>

                <div class="flex justify-end mt-4">
                    <Button label="Simpan Spesimen" severity="info" class="mr-2" @click="specimentUpload"/>
                </div>
            </div>
            <div class="font-semibold text-xl">2FA</div>
            <div class="flex flex-col md:flex-row gap-4">
                <InputGroup>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>                     
                    <ToggleSwitch v-else :modelValue="tfa" @update:modelValue="onToggle2FA"/>
                </InputGroup>
                <!-- <InputGroup>
                    <Button label="Setup" severity="info" class="mr-2" v-if="!twofa" @click="twofa = true" />
                </InputGroup> -->
            </div>
            <div class="font-semibold text-xl">Ubah Password</div>
            <div class="flex flex-col md:flex-row gap-4">
                <InputGroup>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>
                    <InputText ref="oldPasswordInput" v-else type="password" class="w-full" v-model="oldPassword" placeholder="Password Lama" />                     
                </InputGroup>
            </div>
            <div class="flex flex-col md:flex-row gap-4">
                <InputGroup>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>
                    <Password v-else type="password" class="w-full" v-model="newPassword" placeholder="Password Baru" :class="{'p-invalid': submitted && newPassword !== confirmPassword}"/>                     
                </InputGroup>
                <InputGroup>
                    <Skeleton width="100%" height="2.5rem" borderRadius="6px" v-if="auth.loadingMe"></Skeleton>
                    <InputText v-else type="password" class="w-full" v-model="confirmPassword" placeholder="Konfirmasi Password Baru" :class="{'p-invalid': submitted && newPassword !== confirmPassword}" />                     
                </InputGroup>
                <InputGroup>
                    <Button label="Ubah Password" severity="info" class="mr-2" @click="submitChangePassword(false)" :loading="auth.loadingCp"/>
                </InputGroup>
            </div>
            <div class="flex justify-end">
            </div>
        </div>
        <Dialog v-model:visible="changePassDialog" :style="{ width: '450px' }" header="Confirm" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle !text-3xl" />
                <span
                    >Apakah Yakin anda ingin mengubah password? Setelah berhasil anda akan logout!</span
                >
            </div>
            <template #footer>
                <Button label="Yes" icon="pi pi-check" @click="submitChangePassword(true)" />
                <Button label="No" icon="pi pi-times" text @click="changePassDialog = false; oldPasswordInput.focus()" />
            </template>
        </Dialog>

        <Dialog v-model:visible="forcePasswordDialog" :style="{ width: '450px' }" header="Pemberitahuan" :modal="true" :closable="false">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle !text-3xl" />
                <span
                    >Anda diwajibkan untuk mengubah password setiap 90 hari. Silahkan ubah password anda untuk melanjutkan.</span
                >
            </div>
            <template #footer>
                <Button label="Paham" icon="pi pi-check" text @click="forcePasswordDialog = false" />
            </template>
        </Dialog>

        <twofasetupDialog
        v-model:visible="show2FADialog"
        :mode="twofaMode"
        @verified="auth.me()"
        />
    </Fluid>
    </div>
</template>
