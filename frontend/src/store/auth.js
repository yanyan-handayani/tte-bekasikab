import api from "@/plugins/api";
import { defineStore } from "pinia";


const PRIVACY_VERSION = 1
export const useAuthStore = defineStore("auth", {
    state: () => ({
        user: null,
        twofa: false,
        accessToken: null,

        step: "credential",
        stepReset: "reset_request", 
        tmpToken: null,
        tempUsername: null,
        tempPassword: null,
        tmpCredential: null,

        qr: null,
        secret: null,
        errorSetup: null,

        loading: false,
        loadingMe: false,
        loadingCp: false,
        loadingL: false,
        error: null,

        role: null,
        sesubunit: null,
        isLoggingOut: false,

        accessToken: localStorage.getItem('access_token'),
        refreshToken: localStorage.getItem('refresh_token'),
        isAuthenticated: !!localStorage.getItem('access_token'),
        privcyPolicy: localStorage.getItem('privacy_accepted'),
        privacyAcceptedVersion: Number(localStorage.getItem('privacy_version')) || null,
    }),
    getters: {
        mustAcceptPrivacy: (state) => {
            return state.privacyAcceptedVersion !== PRIVACY_VERSION
        }
    },
    actions: {
        async login(username, password) {
            this.loading = true
            this.error = null

            try {
                const res = await api.post("token/", {
                    username,
                    password,
                })

                this.accessToken = res.data.access
                this.refreshToken = res.data.refresh
                this.isAuthenticated = true
                this.step = 'credential'

                localStorage.setItem('access_token', res.data.access)
                localStorage.setItem('refresh_token', res.data.refresh)
                localStorage.setItem('privacy_accepted', 'false')
                localStorage.setItem('force_change_password', res.data.force_change_password)
                return res
            } catch (err) {
                if (
                    err.response?.status === 400 &&
                    err.response?.data?.code?.includes('2fa_required')
                ) {
                    this.tempUsername = username
                    this.tempPassword = password

                    this.step = 'otp'
                    this.error = null
                } else {
                    this.error = err.response?.data?.detail?.[0] || 'Login gagal'
                }

                this.isAuthenticated = false
                throw err
            } finally {
                this.loading = false
            }
        },
        async refreshTokenAction() {
            try{
                this.loading = true
                const res = await api.post('/token/refresh/',
                    { refresh: this.refreshToken }
                )
                const access= res.data.access
                this.accessToken = access
                localStorage.setItem('access_token', access)
                return access
                
            }catch(err){
                this.error = err.message
                throw err
            }finally{
                this.loading = false
            }
        },
        async me() {
            this.loadingMe = true
            try{
                const res = await api.get("auth/me")
                this.user = res.data
            }catch(err){
                this.error = err.message
            }finally{
                this.loadingMe = false
            }
        },
        async loadTotpSetup() {
            this.loading = true
            try {
                const res = await api.post('2fa/setup/',{}, { responseType: 'blob' })
                this.qr =  URL.createObjectURL(res.data)
                return res
            }catch(err){
                this.error = err.message
                throw err
            } 
            finally {
                this.loading = false
            }
        },
        async verifyOtp(otp) {
            this.loading = true
            this.error = null

            try {
                const res = await api.post("token/", {
                    username: this.tempUsername,
                    password: this.tempPassword,
                    otp: otp,
                })

                this.accessToken = res.data.access
                this.refreshToken = res.data.refresh
                this.isAuthenticated = true

                localStorage.setItem('access_token', res.data.access)
                localStorage.setItem('refresh_token', res.data.refresh)

                this.tempUsername = null
                this.tempPassword = null
                return res
            } catch (err) {
                this.error = 'OTP tidak valid'
                throw err
            } finally {
                this.loading = false
            }
        },
        async enable2FA(payload) {
            this.loading = true
            try {
                const res = await api.post('2fa/enable/', payload)
            }catch(err){
                const message =
                err?.response?.data?.detail ||
                err?.response?.data?.message ||
                'Terjadi kesalahan'

                this.error = message
                throw new Error(message)
            }finally{
                this.loading = false
            }
        },
        async disable2FA(params) {
            await api.post('2fa/disable/',params)
            this.twofa = false
        },

        async forgotPassword(params) {
            this.loading = true
            this.error = null

            try {
                const res = await api.post("auth/password/reset/request",
                    params,
                )
                this.stepReset = 'setup_reset'
                return res
            } catch (err) {
                this.error = err.response?.data?.detail?.[0] || 'Gagal mengirim email'
                throw err
            } finally {
                this.loading = false
            }
        },
        async resetPassword(params) {
            this.loading = true
            this.error = null
            try {
                const res = await api.post("auth/password/reset/confirm",
                    params,
                )
                return res
            } catch (err) {
                this.error = err.response?.data?.message || err.response?.data?.detail?.[0] || 'Gagal mereset password'
                throw err
            } finally {
                this.loading = false
            }
        },
        async changePassword(params) {
            this.loadingCp = true
            this.error = null
            try {
                const res = await api.post("auth/password/change", params)
                return res
            } catch (err) {
                this.error = err.response?.data?.detail?.[0] || 'Gagal mengganti password'
                throw err
            } finally {
                this.loadingCp = false
            }
        },

        async privacyLog(params) {
            this.loadingL = true
            try{
                const res =await api.post("v1/loguseractivity", params)
                localStorage.setItem('privacy_accepted', 'true')
                return res
            }catch(err){
                throw err
            }finally{
                this.loadingL = false
            }
        },
        finishLogin(data) {
            this.accessToken = data.access_token || this.tmpToken
            localStorage.setItem('token', this.accessToken)
            this.step = 'done'
            
        },

        logout() {
            this.accessToken = null
            this.refreshToken = null
            this.isAuthenticated = false
            this.user = null

            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            localStorage.removeItem('privacy_accepted')

            delete api.defaults.headers.common['Authorization']
        }       
    }
});
