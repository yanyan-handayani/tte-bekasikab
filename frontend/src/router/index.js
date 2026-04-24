import AppLayout from '@/layout/AppLayout.vue';
import { useAuthStore } from '@/store/auth';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            meta: { requiresAuth: true },    
            children: [
                {
                    path: '/',
                    name: 'dashboard',
                    component: () => import('@/views/Dashboard.vue'),
                },
                {
                    path: '/surat',
                    name: 'surat',
                    component: () => import('@/views/pages/Surat.vue'),
                },
                {
                    path: '/surat/:id',
                    name: 'surat-detail',
                    component: () => import('@/views/pages/SuratDetail.vue'),
                    props: true
                },
                {
                    path: '/profile',
                    name: 'profile',
                    component: () => import('@/views/pages/Profile.vue'),
                }
            ]
        },

        {
            path: '/landing',
            name: 'landing',
            component: () => import('@/views/pages/Landing.vue')
        },
        {
            path: '/auth/login',
            name: 'login',
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/auth/forgot-password',
            name: 'forgot-password',
            component: () => import('@/views/pages/auth/ForgotPassword.vue')
        },
        {
            path: '/auth/access',
            name: 'accessDenied',
            component: () => import('@/views/pages/auth/Access.vue')
        },
        {
            path: '/auth/error',
            name: 'error',
            component: () => import('@/views/pages/auth/Error.vue')
        },
        {
            path: '/:pathMatch(.*)*',
            name: 'notfound',
            component: () => import('@/views/pages/NotFound.vue')
        },
        {
            path: '/reset-password',
            name: 'reset-password',
            component: () => import('@/views/pages/auth/ResetPassword.vue'),
        }
    ]
});

// router.beforeEach((to, from, next) => {
//     const auth = useAuthStore()
//     const privacy = localStorage.getItem('privacy_accepted') 
//     const currentPath = router.currentRoute.value.path

//     const requiresAuth = to.matched.some(record => record.meta.requiresAuth)

//     if (requiresAuth && !auth.isAuthenticated) {
//         next({
//             name: 'login',
//             query: { redirect: to.fullPath }
//         })
//         return
//     }

//     if (to.name === 'login' && auth.isAuthenticated) {
//         next({ name: 'dashboard' })
//         return
//     }
//     if (privacy !== 'true' && auth.isAuthenticated && currentPath !== '/auth/login') {
//         auth.logout() 
//         router.push('/auth/login') 
//     }
//     next()
// });

// router.beforeEach((to) => {
//     const auth = useAuthStore()

//     if (to.meta.requiresAuth && !auth.isAuthenticated) {
//         return '/auth/login'
//     }

//     if (to.path === '/auth/login' && auth.isAuthenticated) {
//         return '/'
//     }
// });

router.beforeEach((to) => {
    const auth = useAuthStore();
    const privacyAccepted = localStorage.getItem('privacy_accepted') === 'true';
    const forcePassword = localStorage.getItem('force_change_password') === 'true';
    // Page protected
    if (to.meta.requiresAuth && !auth.isAuthenticated) {
        return { name: 'login', query: { redirect: to.fullPath } };
    }

    // Privacy policy check
    if (auth.isAuthenticated && !privacyAccepted && to.name !== 'privacy-policy') {
        auth.logout();
        return { name: 'login' };
    }

    // Prevent login page access
    if (to.name === 'login' && auth.isAuthenticated) {
        return { name: 'dashboard' };
    }

    //  if forcepassword
    if (auth.isAuthenticated && forcePassword && to.name !== 'profile') {
        return { name: 'profile' };
    }
    return true;
});

export default router;