<script setup>
import { useLayout } from '@/layout/composables/layout';
import { useAuthStore } from '@/store/auth';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AppConfigurator from './AppConfigurator.vue';

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const router = useRouter();
const auth = useAuthStore();
const userMenu = ref(null);

function toggleUserMenu(event) {
    userMenu.value.toggle(event);
}

const userMenuItems = [
    {
        label: 'Profil Saya',
        icon: 'pi pi-user',
        command: () => router.push('/profile')
    },
    {
        separator: true
    },
    {
        label: 'Logout',
        icon: 'pi pi-sign-out',
        command: () => {
            auth.logout();      
            router.push('/auth/login'); 
        }
    }
];
</script>

<template>
    <div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>
            <router-link to="/" class="layout-topbar-logo">
               <img src="/fileassets/logo.png" height="10" width="70" alt="Baper Logo"  class="mr-2" />

                <span></span>
            </router-link>
        </div>

        <div class="layout-topbar-actions gap-0">
            <div class="layout-config-menu" style="gap: 0 !important;">
                <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>
                <div class="relative">
                    <button
                        v-if="false"
                        v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-scalein', leaveToClass: 'hidden', leaveActiveClass: 'animate-fadeout', hideOnOutsideClick: true }"
                        type="button"
                        class="layout-topbar-action layout-topbar-action-highlight"
                    >
                        <i class="pi pi-palette"></i>
                    </button>
                    <AppConfigurator />
                </div>
                
                <button 
                    type="button" 
                    class="layout-topbar-action"
                    @click="toggleUserMenu"
                >
                    <i class="pi pi-user"></i>
                    <span>Profile</span>
                </button>
                <Menu 
                    ref="userMenu"
                    :model="userMenuItems"
                    popup
                />
            </div>

            <button
                v-if="false"
                class="layout-topbar-menu-button layout-topbar-action"
                v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-scalein', leaveToClass: 'hidden', leaveActiveClass: 'animate-fadeout', hideOnOutsideClick: true }"
            >
                <i class="pi pi-ellipsis-v"></i>
            </button>

            <div class="layout-topbar-menu hidden lg:block">
                <div class="layout-topbar-menu-content">
                    <button v-if="false" type="button" class="layout-topbar-action">
                        <i class="pi pi-calendar"></i>
                        <span>Calendar</span>
                    </button>
                    <button v-if="false" type="button" class="layout-topbar-action">
                        <i class="pi pi-inbox"></i>
                        <span>Messages</span>
                    </button>
                   
                </div>
            </div>
        </div>
    </div>
</template>
