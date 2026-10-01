/**
 * Solar Monitor - Main Application Orchestrator
 * Maneja 3 vistas: En Vivo, Histórico (lazy-load), Configuración.
 * Polling de 30s solo en vista "En Vivo". Histórico carga bajo demanda.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicialización de módulos
  const api = new ApiClient();
  const flowDiagram = new FlowDiagram('energyFlowSvg');
  const unifiedChart = new UnifiedChart('unifiedChart');

  // Estado de la aplicación
  let historyLoaded = false;
  let configLoaded = false;
  let currentView = 'live';

  // Elementos DOM para KPIs y Estado
  const dom = {
    // Header
    statusBadge: document.getElementById('system-status-badge'),
    statusText: document.getElementById('system-status-text'),
    telegramBadge: document.getElementById('telegram-badge'),
    telegramText: document.getElementById('telegram-text'),
    deviceSn: document.getElementById('device-sn-text'),
    lastUpdate: document.getElementById('last-update-time'),
    btnRefresh: document.getElementById('btn-refresh'),

    // Alertas
    alertConnection: document.getElementById('alert-connection'),
    alertConnectionText: document.getElementById('alert-connection-text'),
    alertGridLoss: document.getElementById('alert-grid-loss'),
    alertOverload: document.getElementById('alert-overload'),
    alertLowBattery: document.getElementById('alert-low-battery'),

    // KPIs
    kpiSolarVal: document.getElementById('kpi-solar-val'),
    kpiSolarSub: document.getElementById('kpi-solar-sub'),
    kpiLoadVal: document.getElementById('kpi-load-val'),
    kpiLoadSub: document.getElementById('kpi-load-sub'),
    kpiBatteryVal: document.getElementById('kpi-battery-val'),
    kpiBatterySub: document.getElementById('kpi-battery-sub'),
    kpiBatteryBar: document.getElementById('kpi-battery-bar'),
    kpiGridVal: document.getElementById('kpi-grid-val'),
    kpiGridSub: document.getElementById('kpi-grid-sub'),
    kpiTempVal: document.getElementById('kpi-temp-val'),
    kpiTempSub: document.getElementById('kpi-temp-sub'),

    // Resumen de Energía
    totalPvKwh: document.getElementById('total-pv-kwh'),
    totalLoadKwh: document.getElementById('total-load-kwh'),

    // Controles de Modo y Filtros (en pestaña Histórico)
    modeSimpleBtn: document.getElementById('mode-simple-btn'),
    modeExpertBtn: document.getElementById('mode-expert-btn'),
    filterChips: document.querySelectorAll('.filter-chip'),
    historyLoadingBadge: document.getElementById('history-loading-badge'),

    // Navegación de Vistas
    tabLive: document.getElementById('nav-tab-live'),
    tabHistory: document.getElementById('nav-tab-history'),
    tabConfig: document.getElementById('nav-tab-config'),
    viewLive: document.getElementById('view-live'),
    viewHistory: document.getElementById('view-history'),
    viewConfig: document.getElementById('view-config'),

    // Campos de Configuración
    cfgShineUser: document.getElementById('cfg-shinemonitor-user'),
    cfgShinePass: document.getElementById('cfg-shinemonitor-pass'),
    cfgShinePassStatus: document.getElementById('cfg-shinemonitor-pass-status'),
    cfgTelegramEnabled: document.getElementById('cfg-telegram-enabled'),
    cfgTelegramToken: document.getElementById('cfg-telegram-token'),
    cfgTelegramTokenStatus: document.getElementById('cfg-telegram-token-status'),
    cfgTelegramChatId: document.getElementById('cfg-telegram-chat-id'),
    cfgTempMax: document.getElementById('cfg-temp-max'),
    cfgGridRestoreV: document.getElementById('cfg-grid-restore-v'),
    cfgOverloadW: document.getElementById('cfg-overload-w'),
    cfgBatteryLow: document.getElementById('cfg-battery-low'),
    cfgWatchdogTimeout: document.getElementById('cfg-watchdog-timeout'),
    cfgCooldownMin: document.getElementById('cfg-cooldown-min'),
    cfgDailyReportEnabled: document.getElementById('cfg-daily-report-enabled'),
    cfgDailyReportTime: document.getElementById('cfg-daily-report-time'),

    // Botones de Configuración y Feedback
    btnSaveConfig: document.getElementById('btn-save-config'),
    btnTestTelegram: document.getElementById('btn-test-telegram'),
    btnTestDailyReport: document.getElementById('btn-test-daily-report'),
    configSaveStatus: document.getElementById('config-save-status'),
    telegramTestFeedback: document.getElementById('telegram-test-feedback'),
    dailyReportTestFeedback: document.getElementById('daily-report-test-feedback')
  };

  // 2. Actualización de Telemetría en Tiempo Real
  function showConnectionAlert(message) {
    if (!dom.alertConnection) return;
    if (dom.alertConnectionText) dom.alertConnectionText.textContent = message;
    dom.alertConnection.style.display = 'flex';
  }

  function hideConnectionAlert() {
    if (!dom.alertConnection) return;
    dom.alertConnection.style.display = 'none';
    if (dom.alertConnectionText) dom.alertConnectionText.textContent = '';
  }

  async function refreshStatus() {
    dom.btnRefresh.classList.add('spinning');
    try {
      const data = await api.getStatus();

      if (!data || data.status !== 'online' || !data.metrics) {
        const isDemo = data && data.status === 'demo';
        dom.statusBadge.className = isDemo ? 'status-badge demo' : 'status-badge offline';
        dom.statusText.textContent = isDemo ? 'Modo Demo' : 'Desconectado';
        showConnectionAlert((data && data.error) || 'No hay telemetría real del inversor.');
        return;
      }

      hideConnectionAlert();
      dom.statusBadge.className = 'status-badge';
      dom.statusText.textContent = 'En Línea';

      if (data.device_sn) {
        dom.deviceSn.textContent = `SN: ${data.device_sn}`;
      }

      if (data.last_update) {
        const timePart = data.last_update.includes('T')
          ? data.last_update.split('T')[1].substring(0, 8)
          : data.last_update;
        dom.lastUpdate.textContent = timePart;
      }

      const metrics = data.metrics || {};
      const alerts = data.alerts || {};

      // Actualizar Alertas
      dom.alertGridLoss.style.display = alerts.grid_loss ? 'flex' : 'none';
      dom.alertOverload.style.display = alerts.overload_risk ? 'flex' : 'none';
      dom.alertLowBattery.style.display = alerts.low_battery ? 'flex' : 'none';

      // Actualizar KPIs
      dom.kpiSolarVal.textContent = Math.round(metrics.pv_power_w || 0);
      dom.kpiSolarSub.textContent = `${Math.round(metrics.pv_voltage_v || 0)} V`;

      dom.kpiLoadVal.textContent = Math.round(metrics.load_power_w || 0);
      dom.kpiLoadSub.textContent = `${Math.round(metrics.load_percent || 0)}% Capacidad`;

      const batPct = Math.round(metrics.battery_capacity_percent || 0);
      dom.kpiBatteryVal.textContent = batPct;
      dom.kpiBatterySub.textContent = `${(metrics.battery_voltage_v || 0).toFixed(1)} V`;
      if (dom.kpiBatteryBar) dom.kpiBatteryBar.style.width = `${batPct}%`;

      dom.kpiGridVal.textContent = Math.round(metrics.grid_voltage_v || 0);
      dom.kpiGridSub.textContent = `${(metrics.grid_frequency_hz || 0).toFixed(1)} Hz`;

      dom.kpiTempVal.textContent = metrics.temp_c !== undefined ? metrics.temp_c : '--';
      dom.kpiTempSub.textContent = 'Inversor Principal';

      // Actualizar Diagrama de Flujo SVG
      flowDiagram.update(metrics, alerts);

    } catch (err) {
      console.error('Error al actualizar estado:', err);
      dom.statusBadge.className = 'status-badge offline';
      dom.statusText.textContent = 'Error Conexión';
      showConnectionAlert(err.message || 'No se pudo contactar el servidor.');
    } finally {
      setTimeout(() => dom.btnRefresh.classList.remove('spinning'), 600);
    }
  }

  // 3. Carga de Serie Histórica (lazy — solo cuando se pide)
  async function loadHistory(options = {}) {
    const errorEl = document.getElementById('history-error');
    if (dom.historyLoadingBadge) dom.historyLoadingBadge.style.display = 'flex';
    if (errorEl) errorEl.style.display = 'none';
    try {
      const data = await api.getHistory(options);
      if (!data || !Array.isArray(data.history)) {
        throw new Error('Respuesta de histórico inválida');
      }
      if (data.error) {
        throw new Error(data.error);
      }
      unifiedChart.loadHistory(data.history);

      if (data.summary) {
        const pvText = `${data.summary.pv_energy_kwh || 0} kWh`;
        const loadText = `${data.summary.load_energy_kwh || 0} kWh`;

        if (dom.totalPvKwh) dom.totalPvKwh.textContent = data.summary.pv_energy_kwh || '0.0';
        if (dom.totalLoadKwh) dom.totalLoadKwh.textContent = `${data.summary.load_energy_kwh || 0} kWh`;

        const footerSolar = document.getElementById('total-solar-footer');
        const footerLoad = document.getElementById('total-load-footer');
        if (footerSolar) footerSolar.textContent = pvText;
        if (footerLoad) footerLoad.textContent = loadText;
      }
      return true;
    } catch (err) {
      console.error('Error al cargar histórico:', err);
      if (errorEl) {
        errorEl.textContent = err.message || 'No se pudo cargar el histórico.';
        errorEl.style.display = 'block';
      }
      return false;
    } finally {
      if (dom.historyLoadingBadge) dom.historyLoadingBadge.style.display = 'none';
    }
  }

  // 4. Modos de Vista del Gráfico (Simple vs Experto)
  if (dom.modeSimpleBtn) {
    dom.modeSimpleBtn.addEventListener('click', () => {
      dom.modeSimpleBtn.classList.add('active');
      dom.modeExpertBtn.classList.remove('active');
      unifiedChart.setViewMode('simple');
    });
  }

  if (dom.modeExpertBtn) {
    dom.modeExpertBtn.addEventListener('click', () => {
      dom.modeExpertBtn.classList.add('active');
      dom.modeSimpleBtn.classList.remove('active');
      unifiedChart.setViewMode('expert');
    });
  }

  // 5. Filtros Rápidos de Histórico
  dom.filterChips.forEach((chip) => {
    chip.addEventListener('click', async () => {
      dom.filterChips.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');

      const filterType = chip.dataset.filter;

      if (['1h', '2h', '3h', '6h', '12h'].includes(filterType)) {
        unifiedChart.applyFilter(filterType);
      } else if (filterType === 'today') {
        unifiedChart.applyFilter('all');
      } else if (filterType.startsWith('past_')) {
        const daysAgo = parseInt(filterType.replace('past_', ''), 10);
        const targetDate = getDateDaysAgo(daysAgo);
        await loadHistory({ date: targetDate });
        unifiedChart.applyFilter('all');
      } else if (filterType.startsWith('range_')) {
        const daysCount = parseInt(filterType.replace('range_', ''), 10);
        const startDate = getDateDaysAgo(daysCount);
        const endDate = getDateDaysAgo(0);
        await loadHistory({ start_date: startDate, end_date: endDate });
        unifiedChart.applyFilter('all');
      }
    });
  });

  function getDateDaysAgo(daysAgo) {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  // 6. Refresco Manual (header)
  dom.btnRefresh.addEventListener('click', () => {
    refreshStatus();
    // Si estamos en histórico, refrescar también el gráfico
    if (currentView === 'history') {
      loadHistory({ date: getDateDaysAgo(0) });
    }
  });

  // 7. Polling Periódico Automático cada 30 segundos (solo telemetría en vivo)
  const POLLING_INTERVAL_MS = 30000;
  setInterval(() => {
    refreshStatus();
  }, POLLING_INTERVAL_MS);

  async function checkTelegramStatus() {
    try {
      const res = await api.getAlertsStatus();
      if (res && res.telegram_configured && dom.telegramBadge) {
        dom.telegramBadge.style.display = 'inline-flex';
      } else if (dom.telegramBadge) {
        dom.telegramBadge.style.display = 'none';
      }
    } catch (e) {
      console.warn('No se pudo verificar estado de Telegram:', e);
    }
  }

  // 8. Navegación entre 3 Vistas
  function switchView(viewName) {
    currentView = viewName;

    // Desactivar todos los tabs y ocultar todas las vistas
    [dom.tabLive, dom.tabHistory, dom.tabConfig].forEach(t => {
      if (t) { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); }
    });
    [dom.viewLive, dom.viewHistory, dom.viewConfig].forEach(v => {
      if (v) v.style.display = 'none';
    });

    if (viewName === 'live') {
      dom.tabLive.classList.add('active');
      dom.tabLive.setAttribute('aria-selected', 'true');
      dom.viewLive.style.display = 'flex';
    } else if (viewName === 'history') {
      dom.tabHistory.classList.add('active');
      dom.tabHistory.setAttribute('aria-selected', 'true');
      dom.viewHistory.style.display = 'flex';

      // Carga lazy: solo cargar si aún no se ha cargado historia
      if (!historyLoaded) {
        loadHistory({ date: getDateDaysAgo(0) }).then((ok) => {
          if (ok) historyLoaded = true;
        });
      }
    } else if (viewName === 'config') {
      dom.tabConfig.classList.add('active');
      dom.tabConfig.setAttribute('aria-selected', 'true');
      dom.viewConfig.style.display = 'block';
      loadConfigIntoForm();
    }
  }

  dom.tabLive.addEventListener('click', () => switchView('live'));
  dom.tabHistory.addEventListener('click', () => switchView('history'));
  dom.tabConfig.addEventListener('click', () => switchView('config'));

  // 9. Cargar Configuración en Formulario
  async function loadConfigIntoForm() {
    try {
      const cfg = await api.getConfig();
      if (!cfg) throw new Error('Respuesta de configuración vacía');

      if (dom.cfgShineUser) dom.cfgShineUser.value = cfg.shinemonitor_username || '';
      if (dom.cfgShinePass) dom.cfgShinePass.value = '';
      if (dom.cfgShinePassStatus) {
        dom.cfgShinePassStatus.textContent = cfg.shinemonitor_password_set
          ? 'Hay una contrasena guardada. Dejala vacia para conservarla, o escribe una nueva para cambiarla.'
          : 'No hay contrasena guardada.';
      }
      if (dom.cfgTelegramEnabled) dom.cfgTelegramEnabled.checked = cfg.telegram_enabled !== false;
      if (dom.cfgTelegramToken) dom.cfgTelegramToken.value = '';
      if (dom.cfgTelegramTokenStatus) {
        dom.cfgTelegramTokenStatus.textContent = cfg.telegram_bot_token_set
          ? 'Hay un token guardado. Déjalo vacío para conservarlo, o escribe uno nuevo para reemplazarlo.'
          : 'No hay token guardado.';
      }
      if (dom.cfgTelegramChatId) dom.cfgTelegramChatId.value = cfg.telegram_chat_id || '';

      if (dom.cfgTempMax) dom.cfgTempMax.value = cfg.alert_temp_max_c || 75;
      if (dom.cfgGridRestoreV) dom.cfgGridRestoreV.value = cfg.grid_restore_min_v || 180;
      if (dom.cfgOverloadW) dom.cfgOverloadW.value = cfg.alert_overload_w || 6100;
      if (dom.cfgBatteryLow) dom.cfgBatteryLow.value = cfg.alert_low_battery_pct || 20;

      if (dom.cfgWatchdogTimeout) dom.cfgWatchdogTimeout.value = cfg.watchdog_timeout_minutes || 15;
      if (dom.cfgCooldownMin) dom.cfgCooldownMin.value = cfg.alert_cooldown_minutes || 30;

      if (dom.cfgDailyReportEnabled) dom.cfgDailyReportEnabled.checked = cfg.daily_report_enabled !== false;
      if (dom.cfgDailyReportTime) dom.cfgDailyReportTime.value = cfg.daily_report_time || '20:00';
      configLoaded = true;
    } catch (err) {
      configLoaded = false;
      console.error('Error al cargar configuración en el formulario:', err);
      showSaveToast(`No se pudo cargar la configuración: ${err.message}`, 'error');
    }
  }

  // 10. Guardar Configuración
  if (dom.btnSaveConfig) {
    dom.btnSaveConfig.addEventListener('click', async () => {
      if (!configLoaded) {
        showSaveToast('No se guardó: primero tiene que cargar la configuración.', 'error');
        return;
      }
      const token = dom.cfgTelegramToken ? dom.cfgTelegramToken.value.trim() : '';
      const newConfig = {
        shinemonitor_username: (dom.cfgShineUser ? dom.cfgShineUser.value.trim() : ''),
        telegram_enabled: dom.cfgTelegramEnabled ? dom.cfgTelegramEnabled.checked : true,
        telegram_chat_id: dom.cfgTelegramChatId ? dom.cfgTelegramChatId.value.trim() : '',
        alert_temp_max_c: dom.cfgTempMax ? parseFloat(dom.cfgTempMax.value) || 75.0 : 75.0,
        grid_restore_min_v: dom.cfgGridRestoreV ? parseFloat(dom.cfgGridRestoreV.value) || 180.0 : 180.0,
        alert_overload_w: dom.cfgOverloadW ? parseFloat(dom.cfgOverloadW.value) || 6100.0 : 6100.0,
        alert_overload_pct: 85.0,
        alert_low_battery_pct: dom.cfgBatteryLow ? parseFloat(dom.cfgBatteryLow.value) || 20.0 : 20.0,
        watchdog_timeout_minutes: dom.cfgWatchdogTimeout ? parseInt(dom.cfgWatchdogTimeout.value, 10) || 15 : 15,
        alert_cooldown_minutes: dom.cfgCooldownMin ? parseInt(dom.cfgCooldownMin.value, 10) || 30 : 30,
        daily_report_enabled: dom.cfgDailyReportEnabled ? dom.cfgDailyReportEnabled.checked : true,
        daily_report_time: dom.cfgDailyReportTime ? dom.cfgDailyReportTime.value || '20:00' : '20:00'
      };
      if (token) newConfig.telegram_bot_token = token;
      const shinePass = dom.cfgShinePass ? dom.cfgShinePass.value.trim() : '';
      if (shinePass) newConfig.shinemonitor_password = shinePass;

      try {
        dom.btnSaveConfig.disabled = true;
        const saved = await api.saveConfig(newConfig);
        if (dom.cfgTelegramToken) dom.cfgTelegramToken.value = '';
        if (dom.cfgTelegramTokenStatus && saved && saved.telegram_bot_token_set) {
          dom.cfgTelegramTokenStatus.textContent = 'Hay un token guardado. Déjalo vacío para conservarlo, o escribe uno nuevo para reemplazarlo.';
        }
        showSaveToast('✅ Configuración guardada en data/config.json', 'success');
        checkTelegramStatus();
      } catch (err) {
        showSaveToast(`❌ Error al guardar: ${err.message}`, 'error');
      } finally {
        dom.btnSaveConfig.disabled = false;
      }
    });
  }

  function showSaveToast(msg, type = 'success') {
    if (!dom.configSaveStatus) return;
    dom.configSaveStatus.textContent = msg;
    dom.configSaveStatus.className = `save-status-toast show ${type}`;
    setTimeout(() => {
      dom.configSaveStatus.classList.remove('show');
    }, 4500);
  }

  // 11. Probar Bot Telegram
  if (dom.btnTestTelegram) {
    dom.btnTestTelegram.addEventListener('click', async () => {
      const token = dom.cfgTelegramToken ? dom.cfgTelegramToken.value.trim() : '';
      const chatId = dom.cfgTelegramChatId ? dom.cfgTelegramChatId.value.trim() : '';
      dom.telegramTestFeedback.textContent = 'Enviando prueba...';
      dom.telegramTestFeedback.style.color = '#38bdf8';

      try {
        const res = await api.testTelegram(token, chatId);
        if (res.success) {
          dom.telegramTestFeedback.textContent = '✅ ¡Mensaje recibido en Telegram!';
          dom.telegramTestFeedback.style.color = '#34d399';
        } else {
          dom.telegramTestFeedback.textContent = `❌ ${res.error || res.message || 'Fallo de entrega'}`;
          dom.telegramTestFeedback.style.color = '#f87171';
        }
      } catch (e) {
        dom.telegramTestFeedback.textContent = `❌ Error: ${e.message}`;
        dom.telegramTestFeedback.style.color = '#f87171';
      }
    });
  }

  // 12. Probar Reporte Diario Ahora
  if (dom.btnTestDailyReport) {
    dom.btnTestDailyReport.addEventListener('click', async () => {
      dom.dailyReportTestFeedback.textContent = 'Generando y enviando reporte...';
      dom.dailyReportTestFeedback.style.color = '#38bdf8';

      try {
        const res = await api.testDailyReport();
        if (res.success) {
          dom.dailyReportTestFeedback.textContent = '✅ ¡Reporte enviado con éxito!';
          dom.dailyReportTestFeedback.style.color = '#34d399';
        } else {
          dom.dailyReportTestFeedback.textContent = `❌ ${res.error || res.message || 'Fallo al enviar'}`;
          dom.dailyReportTestFeedback.style.color = '#f87171';
        }
      } catch (e) {
        dom.dailyReportTestFeedback.textContent = `❌ Error: ${e.message}`;
        dom.dailyReportTestFeedback.style.color = '#f87171';
      }
    });
  }

  // 13. Carga Inicial — solo live, sin cargar histórico en arranque
  refreshStatus();
  checkTelegramStatus();
});
