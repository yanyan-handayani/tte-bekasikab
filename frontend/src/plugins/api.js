import router from '@/router';
import axios from 'axios';
import { useAuthStore } from '../store/auth';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASEURL,
});


api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("access_token")
        
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        
        return config
    },
    (error) => Promise.reject(error)
)

api.interceptors.response.use(
    res => res,
    async error => {
        const auth = useAuthStore()
        const original = error.config
        if (original.url?.includes('/token/refresh')) {
            auth.logout()
            router.push('/auth/login')
            return Promise.reject(error)
        }
        if (error.response?.status === 401 && !original._retry) {
            original._retry = true
            try {
                const newToken = await auth.refreshTokenAction()
                original.headers.Authorization = `Bearer ${newToken}`
                return api(original)
            } catch (e) {
                auth.logout()
                router.push('/auth/login')
                return Promise.reject(e) 
            }
        }

        return Promise.reject(error)
    }
)
export default api;
