/**
 * Solar Monitor - Energy Flow Diagram Controller
 * Controla la animación SVG en tiempo real de los 4 nodos energéticos y el inversor central.
 */

class FlowDiagram {
  constructor(svgElementId) {
    this.svg = document.getElementById(svgElementId);
    this.elements = {};
    this.init();
  }

  init() {
    if (!this.svg) return;

    // Cachear elementos SVG para actualización de alto rendimiento
    this.elements = {
      // Valores de texto
      solarVal: document.getElementById('svg-solar-val'),
      solarSub: document.getElementById('svg-solar-sub'),
      loadVal: document.getElementById('svg-load-val'),
      loadSub: document.getElementById('svg-load-sub'),
      batteryVal: document.getElementById('svg-battery-val'),
      batterySub: document.getElementById('svg-battery-sub'),
      gridVal: document.getElementById('svg-grid-val'),
      gridSub: document.getElementById('svg-grid-sub'),
      hubVal: document.getElementById('svg-hub-val'),
      hubSub: document.getElementById('svg-hub-sub'),

      // Líneas de flujo animadas
      flowSolar: document.getElementById('flow-line-solar'),
      flowLoad: document.getElementById('flow-line-load'),
      flowBattery: document.getElementById('flow-line-battery'),
      flowGrid: document.getElementById('flow-line-grid'),

      // Nodos
      nodeSolar: document.getElementById('node-solar'),
      nodeLoad: document.getElementById('node-load'),
      nodeBattery: document.getElementById('node-battery'),
      nodeGrid: document.getElementById('node-grid'),
      nodeHub: document.getElementById('node-hub')
    };
  }

  /**
   * Actualiza el diagrama con las métricas recibidas de la API.
   * @param {Object} metrics - metrics de StatusResponse
   * @param {Object} alerts - alerts de StatusResponse
   */
  update(metrics = {}, alerts = {}) {
    if (!this.svg || !this.elements.solarVal) return;

    const pvPower = Math.round(metrics.pv_power_w || 0);
    const pvVoltage = Math.round(metrics.pv_voltage_v || 0);
    const loadPower = Math.round(metrics.load_power_w || 0);
    const loadPct = Math.round(metrics.load_percent || 0);
    const batPct = Math.round(metrics.battery_capacity_percent || 0);
    const batVolt = (metrics.battery_voltage_v || 0).toFixed(1);
    const batChargeA = metrics.battery_charging_a || 0;
    const batDischargeA = metrics.battery_discharging_a || 0;
    const gridVolt = Math.round(metrics.grid_voltage_v || 0);
    const gridFreq = (metrics.grid_frequency_hz || 0).toFixed(1);

    // 1. Actualizar textos de los Nodos
    this.elements.solarVal.textContent = `${pvPower} W`;
    this.elements.solarSub.textContent = `${pvVoltage} V`;

    this.elements.loadVal.textContent = `${loadPower} W`;
    this.elements.loadSub.textContent = `${loadPct}% Carga`;

    this.elements.batteryVal.textContent = `${batPct}%`;
    this.elements.batterySub.textContent = `${batVolt} V`;

    this.elements.gridVal.textContent = `${gridVolt} V`;
    this.elements.gridSub.textContent = gridVolt > 0 ? `${gridFreq} Hz` : 'DESCONECTADA';

    this.elements.hubVal.textContent = `${loadPct}%`;
    this.elements.hubSub.textContent = metrics.temp_c ? `${metrics.temp_c}°C` : 'Operando';

    // 2. Control dinámico de animación de flujo: SOLAR -> INVERSOR
    if (pvPower > 15) {
      this.elements.flowSolar.classList.add('active');
      const duration = Math.max(0.6, 2.5 - (pvPower / 4000) * 1.8);
      this.elements.flowSolar.style.animationDuration = `${duration}s`;
    } else {
      this.elements.flowSolar.classList.remove('active');
    }

    // 3. Control dinámico de flujo: INVERSOR -> HOGAR
    if (loadPower > 15) {
      this.elements.flowLoad.classList.add('active');
      const duration = Math.max(0.6, 2.5 - (loadPower / 4000) * 1.8);
      this.elements.flowLoad.style.animationDuration = `${duration}s`;
    } else {
      this.elements.flowLoad.classList.remove('active');
    }

    // 4. Control dinámico de flujo: BATERÍA (Carga o Descarga)
    if (batChargeA > 0.3) {
      // Inversor hacia batería (Carga)
      this.elements.flowBattery.classList.remove('battery-discharge');
      this.elements.flowBattery.classList.add('battery-charge', 'active');
      this.elements.batterySub.textContent = `+${batChargeA.toFixed(1)}A (${batVolt}V)`;
    } else if (batDischargeA > 0.3) {
      // Batería hacia inversor (Descarga)
      this.elements.flowBattery.classList.remove('battery-charge');
      this.elements.flowBattery.classList.add('battery-discharge', 'active');
      this.elements.batterySub.textContent = `-${batDischargeA.toFixed(1)}A (${batVolt}V)`;
    } else {
      this.elements.flowBattery.classList.remove('active');
    }

    // 5. Control dinámico de flujo: RED ELÉCTRICA
    if (gridVolt === 0 || alerts.grid_loss) {
      this.elements.flowGrid.classList.remove('active');
      this.elements.nodeGrid.style.opacity = '0.5';
    } else {
      this.elements.nodeGrid.style.opacity = '1';
      // Si el consumo supera a la generación y batería no cubre, importa de la red
      if (loadPower > pvPower && batDischargeA < 1) {
        this.elements.flowGrid.classList.add('active');
      } else {
        this.elements.flowGrid.classList.remove('active');
      }
    }
  }
}

window.FlowDiagram = FlowDiagram;
