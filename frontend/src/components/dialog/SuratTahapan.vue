<script setup>
    import { computed, ref, watch } from 'vue'

    const props = defineProps({
    tahapan: {
        type: Object,
        required: true
    },
    loading: Boolean
    })

    const emit = defineEmits(['submit'])

    const actionSelected = ref(null)
    const pendingMessage = ref('')
    const passphrase = ref('')

    const isParaf = computed(() =>
    props.tahapan.sign_type_display?.id_sign === 1
    )

    const isTte = computed(() =>
    props.tahapan.sign_type_display?.id_sign === 2
    )
    watch(() => props.tahapan, (val) => {
      if (val?.sign_type_display?.id_sign === 1) {
        actionSelected.value = 'paraf'
      } else if (val?.sign_type_display?.id_sign === 2) {
        actionSelected.value = 'sign'
      } else {
        actionSelected.value = null
      }
      pendingMessage.value = ''
      passphrase.value = ''
    }, { immediate: true })

    const buttonLabel = computed(() => {
      switch (actionSelected.value) {
        case 'paraf':
          return 'Paraf Dokumen'
        case 'sign':
          return 'Tandatangani Dokumen'
        case 'pending':
          return 'Kembalikan / Pending'
        default:
          return 'Proses'
      }
    })

    const emitSubmit = () => {
    emit('submit', {
        id_tahapan: props.tahapan.id_tahapan,
        action: actionSelected.value,
        message: actionSelected.value === 'pending'
        ? pendingMessage.value
        : null,
        passphrase: actionSelected.value === 'sign'
        ? passphrase.value
        : null
    })
    }
</script>
<template>
  <div class="mt-4">
    <Divider />

    <div class="font-semibold mb-3">
      <!-- Aksi {{ tahapan.sign_type_display.nama }} -->
    </div>

    <!-- RADIO -->
    <div class="flex gap-4">
    </div>
    <!-- PASSPHRASE -->
    <div v-if="isTte" class="mt-3">
      <label class="font-semibold">Passphrase</label>
      <Password
        v-model="passphrase"
        toggleMask
        :feedback="false"
        class="w-full"
        autocomplete="off"
      />
    </div>
    <!-- SUBMIT -->
    <div class="mt-4">
      <Button
        :label="buttonLabel"
        icon="pi pi-check"
        :loading="props.loading"
        :disabled="(isTte && !passphrase) || 
          props.loading
        "
        @click="emitSubmit"
      />
    </div>
  </div>
</template>
