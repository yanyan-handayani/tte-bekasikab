<script setup>
import { useLayout } from '@/layout/composables/layout';
import { useLaporanStore } from "@/store/laporan";
import { onMounted, ref, watch } from 'vue';

const { getPrimary, getSurface, isDarkTheme } = useLayout();

const chartData = ref(null);
const chartOptions = ref(null);

const laporan = useLaporanStore();

onMounted(async () => {
    await laporan.loadLaporanMutasiPcs();
    setChartData();
})
function setChartData() {
    const documentStyle = getComputedStyle(document.documentElement);
    const list = laporan.laporanMutasiPcs?.data ?? [];
    const labels = list.map(item =>
        `${item.nama_barang || '-'} (${item.tahun_barang || '-'})`
    );

    const masuk = list.map(item => item.masuk || 0);
    const keluar = list.map(item => item.keluar || 0);
    return {
        labels: labels,
        datasets: [
            {
                type: 'bar',
                label: 'Masuk',
                backgroundColor: documentStyle.getPropertyValue('--p-primary-400'),
                data: masuk,
                barThickness: 32
            },
            {
                type: 'bar',
                label: 'Keluar',
                backgroundColor: documentStyle.getPropertyValue('--p-primary-300'),
                data: keluar,
                barThickness: 32
            },
            
        ]
    };
}

function setChartOptions() {
    const documentStyle = getComputedStyle(document.documentElement);
    const borderColor = documentStyle.getPropertyValue('--surface-border');
    const textMutedColor = documentStyle.getPropertyValue('--text-color-secondary');

    return {
        maintainAspectRatio: false,
        aspectRatio: 0.8,
        scales: {
            x: {
                stacked: true,
                ticks: {
                    color: textMutedColor
                },
                grid: {
                    color: 'transparent',
                    borderColor: 'transparent'
                }
            },
            y: {
                stacked: true,
                ticks: {
                    color: textMutedColor
                },
                grid: {
                    color: borderColor,
                    borderColor: 'transparent',
                    drawTicks: false
                }
            }
        }
    };
}

watch([getPrimary, getSurface, isDarkTheme], () => {
    chartData.value = setChartData();
    chartOptions.value = setChartOptions();
});

onMounted(() => {
    chartData.value = setChartData();
    chartOptions.value = setChartOptions();
});
</script>

<template>
    <div class="card">
        <div class="font-semibold text-xl mb-4">Grafik Barang</div>
        <Chart type="bar" :data="chartData" :options="chartOptions" class="h-80" />
    </div>
</template>
