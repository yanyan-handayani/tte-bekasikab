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

    watch(() => props.tahapan, () => {
    actionSelected.value = null
    pendingMessage.value = ''
    passphrase.value = ''
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

      <template v-if="isParaf">
        <RadioButton
          v-model="actionSelected"
          name="aksi"
          inputId="paraf"
          value="paraf"
        />
        <label for="paraf">Paraf</label>
      </template>

      <template v-if="isTte">
        <RadioButton
          v-model="actionSelected"
          name="aksi"
          inputId="sign"
          value="sign"
        />
        <label for="sign">Tandatangani</label>
      </template>

      <RadioButton
        v-model="actionSelected"
        name="aksi"
        inputId="pending"
        value="pending"
      />
      <label for="pending">Pending</label>
    </div>

    <!-- PASSPHRASE (khusus TTE) -->
    <div v-if="actionSelected === 'sign'" class="mt-3">
      <label class="font-semibold">Passphrase</label>
      <Password
        v-model="passphrase"
        toggleMask
        :feedback="false"
        class="w-full"
        autocomplete="off"
      />
    </div>

    <!-- PENDING MESSAGE -->
    <div v-if="actionSelected === 'pending'" class="mt-3">
      <label class="font-semibold">Pesan Pending</label>
      <Textarea
        v-model="pendingMessage"
        rows="4"
        class="w-full"
      />
    </div>

    <!-- SUBMIT -->
    <div class="mt-4">
      <Button
        label="Proses"
        icon="pi pi-check"
        :loading="props.loading"
        :disabled="!actionSelected || 
          (actionSelected === 'pending' && !pendingMessage) ||
          (actionSelected === 'sign' && !passphrase) || 
          props.loading
        "
        @click="emitSubmit"
      />
    </div>
  </div>
</template>
