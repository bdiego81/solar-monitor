/**
 * Solar Monitor - API Client Module
 * Desacopla las llamadas HTTP a la API de FastAPI con manejo de errores y fallbacks.
 */

class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.primaryStatusUrl = `${this.baseUrl}/api/v1/status`;
    this.fallbackStatusUrl = `${this.baseUrl}/api/status`;
    this.primaryHistoryUrl = `${this.baseUrl}/api/v1/history`;
    this.fallbackHistoryUrl = `${this.baseUrl}/api/history`;
  }

  /**
   * Consulta el estado y telemetría en tiempo real.
   * @returns {Promise<Object>} Datos del endpoint /status
   */
  async _fetchJson(urls, label) {
    let lastError = new Error(`No se pudo consultar ${label}`);
    for (const url of urls) {
      let response;
      try {
        response = await fetch(url);
      } catch (error) {
        lastError = new Error(`Sin respuesta al consultar ${label}`);
        continue;
      }
      if (!response.ok) {
        lastError = new Error(`HTTP ${response.status} al consultar ${label}`);
        continue;
      }
      try {
        return await response.json();
      } catch (error) {
        throw new Error(`Respuesta inválida al consultar ${label}`);
      }
    }
    throw lastError;
  }

  async getStatus() {
    if (window.location.protocol === 'file:') {
      return this._mockStatus();
    }
    return this._fetchJson([this.primaryStatusUrl, this.fallbackStatusUrl], 'estado');
  }

  /**
   * Consulta la serie histórica de telemetría e integración de energía.
   * @param {Object} options - { date, start_date, end_date }
   * @returns {Promise<Object>} Datos de /history
   */
  async getHistory(options = {}) {
    if (window.location.protocol === 'file:') {
      return this._mockHistory();
    }
    const params = new URLSearchParams();
    if (options.date) params.append('date', options.date);
    if (options.start_date) params.append('start_date', options.start_date);
    if (options.end_date) params.append('end_date', options.end_date);

    const queryString = params.toString() ? `?${params.toString()}` : '';
    return this._fetchJson(
      [`${this.primaryHistoryUrl}${queryString}`, `${this.fallbackHistoryUrl}${queryString}`],
      'histórico'
    );
  }

  async getAlertsStatus() {
    if (window.location.protocol === 'file:') {
      return { telegram_configured: false };
    }
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/alerts/status`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Error al consultar estado de alertas:', e);
    }
    return null;
  }

  async getConfig() {
    if (window.location.protocol === 'file:') {
      return this._mockConfig();
    }
    return this._fetchJson([`${this.baseUrl}/api/v1/config`], 'configuración');
  }

  async saveConfig(data) {
    if (window.location.protocol === 'file:') {
      return { success: true, message: 'Modo local: Configuración simulada' };
    }
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Error al guardar');
      }
      return await res.json();
    } catch (e) {
      throw e;
    }
  }

  async testTelegram(token, chatId) {
    if (window.location.protocol === 'file:') {
      return { success: true, message: 'Modo archivo local: Simulación de test exitosa' };
    }
    try {
      const body = (token || chatId) ? JSON.stringify({ token, chat_id: chatId }) : null;
      const headers = body ? { 'Content-Type': 'application/json' } : {};
      const res = await fetch(`${this.baseUrl}/api/v1/alerts/test-telegram`, {
        method: 'POST',
        headers,
        body
      });
      return await res.json();
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  async testShineMonitor(username, password) {
    if (window.location.protocol === 'file:') {
      return { success: true, message: 'Modo local: Conexión simulada con inversor exitosa' };
    }
    try {
      const body = (username || password) ? JSON.stringify({ username, password }) : null;
      const headers = body ? { 'Content-Type': 'application/json' } : {};
      const res = await fetch(`${this.baseUrl}/api/v1/config/test-shinemonitor`, {
        method: 'POST',
        headers,
        body
      });
      return await res.json();
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  async testDailyReport() {
    if (window.location.protocol === 'file:') {
      return { success: true, message: 'Modo archivo local: Reporte simulado' };
    }
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/alerts/test-daily-report`, { method: 'POST' });
      return await res.json();
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  _mockConfig() {
    return {
      telegram_bot_token_set: false,
      shinemonitor_password_set: false,
      telegram_chat_id: '',
      telegram_enabled: true,
      alert_temp_max_c: 75.0,
      alert_overload_w: 6100.0,
      alert_overload_pct: 85.0,
      alert_low_battery_pct: 20.0,
      grid_restore_min_v: 180.0,
      watchdog_timeout_minutes: 15,
      daily_report_enabled: true,
      daily_report_time: '20:00',
      alert_cooldown_minutes: 30
    };
  }

  _mockStatus() {
    return {
      status: 'demo',
      device_sn: 'DEMO-SOLAR-5KW',
      last_update: new Date().toISOString(),
      alerts: { grid_loss: false, overload_risk: false, low_battery: false },
      metrics: {
        pv_power_w: 2850,
        pv_voltage_v: 340,
        load_power_w: 820,
        load_voltage_v: 230,
        load_percent: 16.4,
        battery_capacity_percent: 88,
        battery_voltage_v: 52.4,
        battery_charging_a: 38.7,
        battery_discharging_a: 0.0,
        grid_voltage_v: 228,
        grid_frequency_hz: 50.0,
        temp_c: 37.4
      },
      ratings: {
        max_power_w: 5000,
        nominal_battery_v: 48
      }
    };
  }

  _mockHistory() {
    const history = [];
    let totalPvWh = 0;
    let totalLoadWh = 0;
    for (let m = 0; m < 24 * 60; m += 5) {
      const h = m / 60;
      const hoursStr = String(Math.floor(h)).padStart(2, '0');
      const minsStr = String(m % 60).padStart(2, '0');
      const pv = (h >= 7 && h <= 18.5) ? Math.max(0, 3200 * (1 - Math.pow((h - 13) / 5.2, 2))) : 0;
      let load = 480;
      if (h >= 12 && h <= 14) load += 550;
      if (h >= 19 && h <= 23) load += 750;
      const bat = pv > load ? 95 : Math.max(30, 95 - (h * 3));
      totalPvWh += pv * (5 / 60);
      totalLoadWh += load * (5 / 60);

      history.push({
        timestamp: `${hoursStr}:${minsStr}`,
        pv_power_w: Math.round(pv),
        load_power_w: Math.round(load),
        battery_pct: Math.round(bat),
        grid_voltage_v: 230,
        temp_c: 30 + Math.round((load / 5000) * 45)
      });
    }

    return {
      dates: ['2026-09-23'],
      history,
      summary: {
        pv_energy_kwh: +(totalPvWh / 1000).toFixed(2),
        load_energy_kwh: +(totalLoadWh / 1000).toFixed(2)
      }
    };
  }
}

// Exportación global para navegadores o módulos ES6
window.ApiClient = ApiClient;
