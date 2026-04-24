import api from "@/plugins/api";
import { defineStore } from "pinia";

export const useProfileStore = defineStore("profile", {
    state: () => ({
        loading: false,
        error: null,
    }),
    actions: {
        async patchSpecimen(id, formData) {
            this.loading = true
            this.error = null   
            try {
                const res = await api.patch(`v1/pegawai/${id}/specimen/`, formData)
                return true
            } catch (err) {
                this.error = err.response?.data || err.message
                throw err
            }finally {
                this.loading = false
            }
        },
    }
})