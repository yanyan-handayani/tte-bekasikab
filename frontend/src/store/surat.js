import api from '@/plugins/api';
import { defineStore } from "pinia";

export const UseSuratStore = defineStore("surat", {
    state: () => ({
        list: [],
        detail: {},

        loadingFs: false,
        loading: false,
        error: null,

        pagination: {
            page: 1,
            pageSize: 10,
            total: 0,
        },

        filters: {
            search: "",
            status: null,
        },
        suratTpl: [],
    }),
    actions: {
        async fetchSurat(params = {}) {
            this.loadingFs = true;
            this.error = null;
            try {
                this.loadingFs = true
                const res = await api.get("v1/core/surat/", { params
                });
                this.list = res.data.results ?? res.data;
                this.pagination.total = res.data.count ?? this.list.length;
            } catch (err) {
                this.error = err.response?.data || err.message;
            } finally {
                this.loadingFs = false;
            }
        },

        async fetchSuratById(id) {
            this.loading = true;
            this.error = null;

            try {
                const res = await api.get(`v1/core/surat/${id}/`);
                this.detail[id] = res.data;
                return res.data;
            } catch (err) {
                this.error = err.response?.data || err.message;
                throw err;
            } finally {
                this.loading = false;
            }
        },

        async createSurat(payload) {
            this.loading = true;
            this.error = null;

            try {
                const res = await api.post("v1/core/surat/create-with-pdf/", payload);
            } catch (err) {
                this.error = err.response?.data || err.message;
                throw err;  
            } finally {
                this.loading = false;
            }
        },
        async deleteSurat(id) {
            this.loading = true;
            this.error = null;
            try {
                const res = await api.delete(`v1/core/surat/${id}/`);
            } catch (err) {
                this.error = err.response?.data || err.message;
                throw err;  
            } finally {
                this.loading = false;
            }
        },
        async parafSurat(id) {
            this.loading = true;
            this.error = null;
            try {
                const res = await api.post(`v1/core/tahapan/${id}/paraf/`);
                
            } catch (err) {
                this.error = err.response?.data || err.message;
                throw err;  
            } finally {
                this.loading = false;
            }
        },

        async signSurat(id,passphrase) {
            this.loading = true;
            this.error = null;
            try {
                const res = await api.post(`v1/core/tahapan/${id}/sign/`,{passphrase:passphrase});
            } catch (err) {
                this.error = err.response?.data || err.message;
                throw err;  
            } finally {
                this.loading = false;
            }
        },

        async suratTemplateList() {
            this.loading = true;
            this.error = null;
            try {
                const res = await api.get(`v1/surat-templates/`);
                this.suratTpl = res.data.results;
                return res.data;
            } catch (err) {
                this.error = err.response?.data || err.message;
                throw err;  
            } finally {
                this.loading = false;
            }            
        },
    }
})