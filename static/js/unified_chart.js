/**
 * Solar Monitor - Unified Chart.js Controller
 * Gestiona el gráfico principal multi-eje, modos Simple vs Experto y filtrado dinámico.
 */

class UnifiedChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.chart = null;
    this.viewMode = 'simple'; // 'simple' | 'expert'
    this.activeFilter = '3h'; // default filter: last 3 hours
    this.fullHistory = []; // datos completos del día/rango precargado

    this.initChart();
  }

  initChart() {
    if (!this.canvas) return;
    const ctx = this.canvas.getContext('2d');

    // Gradientes elegantes para las áreas de curva
    const solarGradient = ctx.createLinearGradient(0, 0, 0, 350);
    solarGradient.addColorStop(0, 'rgba(245, 158, 11, 0.35)');
    solarGradient.addColorStop(1, 'rgba(245, 158, 11, 0.0)');

    const loadGradient = ctx.createLinearGradient(0, 0, 0, 350);
    loadGradient.addColorStop(0, 'rgba(56, 189, 248, 0.35)');
    loadGradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

    const config = {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          // 0: Solar
          {
            label: 'Solar (W)',
            data: [],
            borderColor: '#f59e0b',
            backgroundColor: solarGradient,
            borderWidth: 2.2,
            fill: true,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 5,
            yAxisID: 'yPower'
          },
          // 1: Consumo
          {
            label: 'Consumo (W)',
            data: [],
            borderColor: '#38bdf8',
            backgroundColor: loadGradient,
            borderWidth: 2.2,
            fill: true,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 5,
            yAxisID: 'yPower'
          },
          // 2: Batería
          {
            label: 'Batería (%)',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'transparent',
            borderWidth: 1.8,
            borderDash: [4, 4],
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
            yAxisID: 'yPercent',
            hidden: true
          },
          // 3: Temperatura Inversor
          {
            label: 'Temp Inversor (°C)',
            data: [],
            borderColor: '#f97316',
            backgroundColor: 'transparent',
            borderWidth: 1.8,
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
            yAxisID: 'yTemp',
            hidden: true
          },
          // 4: Tensión Red
          {
            label: 'Red (V)',
            data: [],
            borderColor: '#a855f7',
            backgroundColor: 'transparent',
            borderWidth: 1.6,
            borderDash: [2, 2],
            fill: false,
            tension: 0.2,
            pointRadius: 0,
            pointHoverRadius: 4,
            yAxisID: 'yVolt',
            hidden: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: '#94a3b8',
              font: { family: 'Inter', size: 12 },
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 18,
              filter: (legendItem) => {
                // En modo Simple, ocultar etiquetas de la leyenda de batería, temp y red
                if (this.viewMode === 'simple') {
                  return legendItem.datasetIndex < 2;
                }
                return true;
              }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.92)',
            titleColor: '#f8fafc',
            bodyColor: '#cbd5e1',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            usePointStyle: true,
            callbacks: {
              label: (context) => {
                let label = context.dataset.label || '';
                let val = context.parsed.y !== null ? context.parsed.y : '';
                if (label.includes('(W)')) return `${label}: ${Math.round(val)} W`;
                if (label.includes('(%)')) return `${label}: ${Math.round(val)} %`;
                if (label.includes('(°C)')) return `${label}: ${val.toFixed(1)} °C`;
                if (label.includes('(V)')) return `${label}: ${Math.round(val)} V`;
                return `${label}: ${val}`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: {
              color: '#64748b',
              font: { family: 'Inter', size: 11 },
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 12
            }
          },
          yPower: {
            type: 'linear',
            position: 'left',
            beginAtZero: true,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#94a3b8',
              font: { family: 'Inter', size: 11 },
              callback: (val) => `${val} W`
            }
          },
          yPercent: {
            type: 'linear',
            position: 'right',
            min: 0,
            max: 100,
            display: false,
            grid: { drawOnChartArea: false },
            ticks: {
              color: '#10b981',
              callback: (val) => `${val}%`
            }
          },
          yTemp: {
            type: 'linear',
            position: 'right',
            min: 20,
            max: 85,
            display: false,
            grid: { drawOnChartArea: false },
            ticks: { display: false }
          },
          yVolt: {
            type: 'linear',
            position: 'right',
            min: 160,
            max: 260,
            display: false,
            grid: { drawOnChartArea: false },
            ticks: { display: false }
          }
        }
      }
    };

    this.chart = new Chart(ctx, config);
  }

  /**
   * Cambia el modo de visualización: Simple vs Experto
   * @param {'simple' | 'expert'} mode
   */
  setViewMode(mode) {
    this.viewMode = mode;
    if (!this.chart) return;

    const isExpert = mode === 'expert';

    // Datasets secundarios: Batería (2), Temp (3), Red (4)
    this.chart.data.datasets[2].hidden = !isExpert;
    this.chart.data.datasets[3].hidden = !isExpert;
    this.chart.data.datasets[4].hidden = !isExpert;

    // Ejes secundarios
    this.chart.options.scales.yPercent.display = isExpert;

    this.chart.update();
  }

  /**
   * Carga una nueva serie de datos completa y aplica el filtro activo.
   * @param {Array} historyPoints - Lista de puntos históricos [{ timestamp, pv_power_w, ... }]
   */
  loadHistory(historyPoints = []) {
    this.fullHistory = historyPoints || [];
    this.applyFilter(this.activeFilter);
  }

  /**
   * Aplica el filtro de tiempo localmente o guarda el filtro actual.
   * @param {string} filterKey - '1h' | '2h' | '3h' | '6h' | '12h' | 'all'
   */
  applyFilter(filterKey) {
    this.activeFilter = filterKey;
    if (!this.chart || this.fullHistory.length === 0) return;

    let displayData = [...this.fullHistory];

    // Cálculo de puntos a mostrar (asumiendo intervalo de 5 min)
    const pointsMap = {
      '1h': 12,
      '2h': 24,
      '3h': 36,
      '6h': 72,
      '12h': 144,
      'all': displayData.length
    };

    if (pointsMap[filterKey] && filterKey !== 'all') {
      const sliceCount = pointsMap[filterKey];
      displayData = displayData.slice(-sliceCount);
    }

    // Formatear etiquetas de tiempo para legibilidad
    const labels = displayData.map((d) => {
      const parts = (d.timestamp || '').split(' ');
      return parts.length > 1 ? parts[1].substring(0, 5) : d.timestamp;
    });

    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = displayData.map((d) => d.pv_power_w);
    this.chart.data.datasets[1].data = displayData.map((d) => d.load_power_w);
    this.chart.data.datasets[2].data = displayData.map((d) => d.battery_pct);
    this.chart.data.datasets[3].data = displayData.map((d) => d.temp_c);
    this.chart.data.datasets[4].data = displayData.map((d) => d.grid_voltage_v);

    this.chart.update();
  }
}

window.UnifiedChart = UnifiedChart;
