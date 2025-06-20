// app.js - Biomarker Dashboard Frontend (Enhanced)

let isDarkMode = false;

function setTheme(dark) {
  document.body.classList.toggle('dark', dark);
  localStorage.setItem('theme', dark ? 'dark' : 'light');
  document.getElementById('theme-toggle').textContent = dark ? '☀️ Light Mode' : '🌙 Dark Mode';
}

function initTheme() {
  const saved = localStorage.getItem('theme');
  setTheme(saved === 'dark');
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  document.getElementById('theme-toggle').onclick = () => {
    isDarkMode = !document.body.classList.contains('dark');
    setTheme(isDarkMode);
  };
});

async function fetchDashboardData() {
  const res = await fetch('dashboard_data.json');
  return await res.json();
}

function deduplicateReports(reports) {
  // For each date, keep only the latest report for each biomarker
  const deduped = {};
  for (const report of reports) {
    const date = report.report_date.slice(0, 10);
    if (!deduped[date]) deduped[date] = {};
    for (const [biomarker, value] of Object.entries(report.biomarkers)) {
      deduped[date][biomarker] = value;
    }
  }
  // Convert back to array of {date, biomarkers}
  return Object.entries(deduped).map(([date, biomarkers]) => ({ report_date: date, biomarkers }));
}

function renderPatientInfo(profile, dedupedReports) {
  const el = document.getElementById('patient-info');
  el.innerHTML = `
    <strong>${profile.name}</strong> &mdash; Age: ${profile.age || '-'} | Gender: ${profile.gender || '-'}
    <br>
    Reports: ${dedupedReports.length} | Monitoring: ${dedupedReports[0]?.report_date || '-'} to ${dedupedReports.at(-1)?.report_date || '-'}
  `;
}

// --- Anonymize Helper ---
function anonymizeText(text) {
  if (!text) return '-';
  return 'Patient #' + (text.length ? text.charCodeAt(0) : Math.floor(Math.random()*10000));
}

// --- Render Patient Snapshot (Clinical Header) ---
function renderPatientSnapshot(profile, dedupedReports) {
  const el = document.getElementById('patient-snapshot');
  if (!el) return;
  const anonymize = document.body.classList.contains('anonymize');
  // Calculate monitoring range
  const dates = dedupedReports.map(r => new Date(r.report_date)).sort((a, b) => a - b);
  const start = dates[0] ? dates[0].toISOString().slice(0, 10) : '-';
  const end = dates.at(-1) ? dates.at(-1).toISOString().slice(0, 10) : '-';
  // Data density: average days between tests
  let density = '-';
  if (dates.length > 1) {
    let totalGap = 0;
    for (let i = 1; i < dates.length; i++) {
      totalGap += (dates[i] - dates[i - 1]) / (1000 * 60 * 60 * 24);
    }
    density = `Avg: ${Math.round(totalGap / (dates.length - 1))} days between tests`;
  }
  // Last updated: latest report date
  const lastUpdated = end !== '-' ? `Last updated: ${end}` : '';
  el.innerHTML = `
    <div class="snapshot-item"><span class="snapshot-label">Patient:</span> <span class="snapshot-value">${anonymize ? anonymizeText(profile.name) : (profile.name || '-')}</span></div>
    <div class="snapshot-item"><span class="snapshot-label">Age:</span> <span class="snapshot-value">${profile.age || '-'}</span></div>
    <div class="snapshot-item"><span class="snapshot-label">Gender:</span> <span class="snapshot-value">${profile.gender || '-'}</span></div>
    <div class="snapshot-item"><span class="snapshot-label">Reports:</span> <span class="snapshot-value">${dedupedReports.length}</span></div>
    <div class="snapshot-item"><span class="snapshot-label">Monitoring:</span> <span class="snapshot-value">${start} to ${end}</span></div>
    <div class="snapshot-item snapshot-density">${density}</div>
    <div class="snapshot-item snapshot-updated">${lastUpdated}</div>
  `;
}

// --- Render Summary Cards (Metric Overview) ---
function renderSummary(stats, dedupedReports, alerts) {
  const el = document.getElementById('summary');
  if (!el) return;
  // Calculate unique biomarkers
  let uniqueBiomarkers = new Set();
  for (const report of dedupedReports) {
    Object.keys(report.biomarkers).forEach(b => uniqueBiomarkers.add(b));
  }
  // Count critical alerts
  const criticalCount = (alerts || []).filter(a => a.severity === 'high' || a.status?.toLowerCase().includes('critical') || a.status === 'High').length;
  // Monitoring duration
  let monitoringDays = '-';
  if (dedupedReports.length > 1) {
    const dates = dedupedReports.map(r => new Date(r.report_date)).sort((a, b) => a - b);
    monitoringDays = Math.round((dates.at(-1) - dates[0]) / (1000 * 60 * 60 * 24));
  }
  const cards = [
    {
      title: 'Total Reports',
      value: dedupedReports.length,
      desc: 'Lab reports analyzed',
      emoji: '🧾',
      color: 'var(--accent2)'
    },
    {
      title: 'Total Biomarker Readings',
      value: uniqueBiomarkers.size,
      desc: 'Unique biomarkers tracked',
      emoji: '🧪',
      color: 'var(--info)'
    },
    {
      title: 'Monitoring Duration',
      value: monitoringDays !== '-' ? monitoringDays + ' days' : '-',
      desc: 'Time span of data',
      emoji: '⏱️',
      color: 'var(--accent)'
    },
    {
      title: 'Critical Alerts',
      value: criticalCount,
      desc: 'Critical out-of-range values',
      emoji: criticalCount > 0 ? '🚨' : '✅',
      color: criticalCount > 0 ? 'var(--danger)' : 'var(--accent2)'
    }
  ];
  el.innerHTML = '';
  for (const card of cards) {
    const div = document.createElement('div');
    div.className = 'summary-card';
    div.style.borderColor = card.color;
    div.innerHTML = `<span class="summary-emoji">${card.emoji}</span><h2>${card.value}</h2><p>${card.title}</p><p>${card.desc}</p>`;
    el.appendChild(div);
  }
}

function renderAlerts(alerts) {
  const el = document.getElementById('alerts');
  el.innerHTML = '';
  if (!alerts.length) {
    el.innerHTML = '<div class="alert">No alerts. All biomarkers are within normal range.</div>';
    return;
  }
  for (const alert of alerts) {
    const div = document.createElement('div');
    div.className = 'alert' + (alert.severity === 'high' ? ' high' : '');
    div.innerHTML = `<strong>${alert.biomarker || ''}</strong>: ${alert.message}<br><em>${alert.recommendation || ''}</em>`;
    el.appendChild(div);
  }
}

function getStatusColor(status) {
  if (status === 'High') return '#ef4444';
  if (status === 'Low') return '#f59e42';
  return '#10b981'; // Normal
}

// --- Audit Trail ---
function logAudit(action) {
  const logs = JSON.parse(localStorage.getItem('audit_trail') || '[]');
  logs.push({ action, time: new Date().toISOString() });
  localStorage.setItem('audit_trail', JSON.stringify(logs));
}
logAudit('view_dashboard');

// --- Reference Range Customization ---
function openRefRangeModal(biomarker, currentRange, onSave) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.innerHTML = `<div class="modal-content"><span class="close" id="close-ref-modal">&times;</span><h3>Edit Reference Range: ${biomarker}</h3><label>Min: <input id="ref-min" type="number" value="${currentRange.min}"></label><br><label>Max: <input id="ref-max" type="number" value="${currentRange.max}"></label><br><button id="save-ref">Save</button></div>`;
  document.body.appendChild(modal);
  document.getElementById('close-ref-modal').onclick = () => modal.remove();
  document.getElementById('save-ref').onclick = () => {
    const min = parseFloat(document.getElementById('ref-min').value);
    const max = parseFloat(document.getElementById('ref-max').value);
    onSave({ min, max });
    modal.remove();
  };
}
function getCustomRef(biomarker) {
  const refs = JSON.parse(localStorage.getItem('custom_refs') || '{}');
  return refs[biomarker];
}
function setCustomRef(biomarker, range) {
  const refs = JSON.parse(localStorage.getItem('custom_refs') || '{}');
  refs[biomarker] = range;
  localStorage.setItem('custom_refs', JSON.stringify(refs));
}

// --- Trend Prediction (simple linear regression) ---
function predictNextValue(dates, values) {
  if (values.length < 2) return null;
  // Convert dates to numbers (days since first)
  const t0 = new Date(dates[0]).getTime();
  const xs = dates.map(d => (new Date(d).getTime() - t0) / (1000*60*60*24));
  const ys = values;
  const n = xs.length;
  const xmean = xs.reduce((a,b) => a+b,0)/n;
  const ymean = ys.reduce((a,b) => a+b,0)/n;
  let num=0, den=0;
  for(let i=0;i<n;i++){ num+=(xs[i]-xmean)*(ys[i]-ymean); den+=(xs[i]-xmean)**2; }
  const slope = den ? num/den : 0;
  const intercept = ymean - slope*xmean;
  const nextX = xs[xs.length-1]+(xs[1]-xs[0]||1);
  return Math.round((slope*nextX+intercept)*100)/100;
}

// --- Comparative Analytics (static demo) ---
const populationAverages = {
  'Total Cholesterol': 170,
  'Triglycerides': 120,
  'Vitamin D': 25,
  'Creatinine': 1.0,
  'HbA1c': 5.5,
  'LDL': 90,
  'HDL': 45,
  'Vitamin B12': 350
};

// --- API Integration Info ---
function renderApiInfo() {
  const el = document.getElementById('api-info');
  if (!el) return;
  el.innerHTML = `<div class="api-info-card">
    <h3>API Integration</h3>
    <p>Connect your LIS/EMR system to this dashboard using our REST API.</p>
    <pre style="background:#111827;color:#FF204E;padding:0.7em 1em;border-radius:0.7em;font-size:1.1em;overflow-x:auto;">POST /api/upload_lab_report\nGET /api/patient/:id/biomarkers</pre>
  </div>`;
}

// --- Animated Transitions ---
function animateTable() {
  const table = document.querySelector('.clinical-table');
  if (table) table.classList.add('animate-table');
}

// --- Accessibility Improvements ---
document.getElementById('theme-toggle').setAttribute('tabindex', '0');
document.getElementById('theme-toggle').setAttribute('aria-pressed', 'false');
document.getElementById('theme-toggle').onkeydown = function(e){if(e.key==='Enter'){this.click();}};

// --- ENHANCED CHARTS AND TABLE RENDERING ---
function renderCharts(trends, dedupedReports) {
  const el = document.getElementById('charts');
  el.innerHTML = '';
  // Fallback: if no trends, use dedupedReports to plot basic charts
  if ((!trends || Object.keys(trends).length === 0) && dedupedReports.length > 0) {
    // Find all unique biomarkers
    let allBiomarkers = new Set();
    dedupedReports.forEach(r => Object.keys(r.biomarkers).forEach(b => allBiomarkers.add(b)));
    allBiomarkers = Array.from(allBiomarkers);
    for (const key of allBiomarkers) {
      const values = [];
      const labels = [];
      const pointColors = [];
      const units = [];
      const statuses = [];
      const refs = [];
      for (const report of dedupedReports) {
        const biomarkerObj = report.biomarkers[key];
        if (biomarkerObj && typeof biomarkerObj === 'object' && biomarkerObj.value !== undefined) {
          values.push(biomarkerObj.value);
          labels.push(report.report_date);
          units.push(biomarkerObj.unit || '');
          statuses.push(biomarkerObj.status || '');
          refs.push(biomarkerObj.reference_range ? `${biomarkerObj.reference_range.min} - ${biomarkerObj.reference_range.max} ${biomarkerObj.unit || ''}` : '');
          pointColors.push(getStatusColor(biomarkerObj.status));
        }
      }
      const card = document.createElement('div');
      card.className = 'chart-card';
      card.innerHTML = `<h3>${key}</h3><canvas></canvas>`;
      el.appendChild(card);
      const ctx = card.querySelector('canvas').getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: key,
            data: values,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37,99,235,0.08)',
            pointRadius: 5,
            pointBackgroundColor: pointColors,
            pointBorderColor: '#fff',
            pointHoverRadius: 7,
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          plugins: {
            legend: { display: false },
            tooltip: {
              enabled: true,
              callbacks: {
                title: ctx => `Date: ${ctx[0].label}`,
                label: ctx => {
                  const i = ctx.dataIndex;
                  return [
                    `Value: ${ctx.parsed.y} ${units[i]}`,
                    `Status: ${statuses[i]}`,
                    refs[i] ? `Ref: ${refs[i]}` : ''
                  ].filter(Boolean);
                }
              }
            },
            title: { display: false }
          },
          interaction: { mode: 'nearest', intersect: false },
          hover: { mode: 'nearest', intersect: false },
          scales: {
            x: { title: { display: true, text: 'Date' } },
            y: { title: { display: true, text: 'Value' }, beginAtZero: false }
          },
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 900, easing: 'easeOutQuart' }
        }
      });
    }
    return;
  }
  // Normal: use trends as before
  if (!trends || Object.keys(trends).length === 0) {
    el.innerHTML = '<div style="grid-column: 1/-1; text-align:center; color:var(--danger); font-size:1.2em;">No biomarker trend data available to display charts.</div>';
    return;
  }
  for (const key in trends) {
    const trend = trends[key];
    // Use trend.values and trend.dates for chart data
    const values = trend.values || [];
    const labels = trend.dates || [];
    const pointColors = values.map((v, i) => {
      // Try to get status from dedupedReports for this date/biomarker
      const report = dedupedReports.find(r => r.report_date === labels[i]);
      const biomarkerObj = report && report.biomarkers[key];
      return getStatusColor(biomarkerObj?.status);
    });
    const units = values.map((v, i) => {
      const report = dedupedReports.find(r => r.report_date === labels[i]);
      const biomarkerObj = report && report.biomarkers[key];
      return biomarkerObj?.unit || '';
    });
    const statuses = values.map((v, i) => {
      const report = dedupedReports.find(r => r.report_date === labels[i]);
      const biomarkerObj = report && report.biomarkers[key];
      return biomarkerObj?.status || '';
    });
    const refs = values.map((v, i) => {
      const report = dedupedReports.find(r => r.report_date === labels[i]);
      const biomarkerObj = report && report.biomarkers[key];
      return biomarkerObj?.reference_range ? `${biomarkerObj.reference_range.min} - ${biomarkerObj.reference_range.max} ${biomarkerObj.unit || ''}` : '';
    });
    const confidences = values.map((v, i) => {
      const report = dedupedReports.find(r => r.report_date === labels[i]);
      const biomarkerObj = report && report.biomarkers[key];
      return biomarkerObj?.confidence !== undefined ? (biomarkerObj.confidence*100).toFixed(0)+'%' : '';
    });
    const sources = values.map((v, i) => {
      const report = dedupedReports.find(r => r.report_date === labels[i]);
      return report?.source_file || '';
    });
    const card = document.createElement('div');
    card.className = 'chart-card';
    card.innerHTML = `<h3>${trend.biomarker} <button class='edit-ref-btn' title='Edit Reference Range' aria-label='Edit Reference Range'>✏️</button></h3><canvas></canvas><div class='compare-avg'>Population Avg: ${populationAverages[key]||'-'}</div>`;
    el.appendChild(card);
    card.querySelector('.edit-ref-btn').onclick = () => {
      const lastObj = dedupedReports.map(r=>r.biomarkers[key]).filter(Boolean).pop();
      openRefRangeModal(key, lastObj?.reference_range||{min:0,max:0}, (range)=>{setCustomRef(key,range);main();});
    };
    const ctx = card.querySelector('canvas').getContext('2d');
    // Trend prediction
    const pred = predictNextValue(labels, values);
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: pred ? [...labels, 'Predicted'] : labels,
        datasets: [{
          label: trend.biomarker,
          data: pred ? [...values, pred] : values,
          borderColor: trend.trend_direction === 'rising' ? '#ef4444' : trend.trend_direction === 'falling' ? '#10b981' : '#2563eb',
          backgroundColor: 'rgba(37,99,235,0.08)',
          pointRadius: 5,
          pointBackgroundColor: pointColors.concat(pred ? ['#f59e42'] : []),
          pointBorderColor: '#fff',
          pointHoverRadius: 7,
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: true,
            callbacks: {
              title: ctx => `Date: ${ctx[0].label}`,
              label: ctx => {
                const i = ctx.dataIndex;
                return [
                  `Value: ${ctx.parsed.y} ${units[i]}`,
                  `Status: ${statuses[i]}`,
                  refs[i] ? `Ref: ${refs[i]}` : '',
                  confidences[i] ? `Confidence: ${confidences[i]}` : '',
                  sources[i] ? `Source: ${sources[i]}` : ''
                ].filter(Boolean);
              }
            }
          },
          title: { display: false }
        },
        interaction: { mode: 'nearest', intersect: false },
        hover: { mode: 'nearest', intersect: false },
        scales: {
          x: { title: { display: true, text: 'Date' } },
          y: { title: { display: true, text: 'Value' }, beginAtZero: false }
        },
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 900, easing: 'easeOutQuart' }
      }
    });
  }
}

function renderTable(dedupedReports) {
  let allBiomarkers = new Set();
  dedupedReports.forEach(r => Object.keys(r.biomarkers).forEach(b => allBiomarkers.add(b)));
  allBiomarkers = Array.from(allBiomarkers);
  const el = document.getElementById('readings-table');
  if (!el) return;
  let html = '<div class="table-scroll"><table class="clinical-table" aria-label="All biomarker readings"><thead><tr><th>Date</th>';
  for (const b of allBiomarkers) html += `<th>${b}</th>`;
  html += '</tr></thead><tbody>';
  for (const report of dedupedReports) {
    html += `<tr><td>${report.report_date}</td>`;
    for (const b of allBiomarkers) {
      const obj = report.biomarkers[b];
      if (obj && typeof obj === 'object' && obj.value !== undefined) {
        // Reference range customization
        const customRef = getCustomRef(b);
        const ref = customRef ? `${customRef.min} - ${customRef.max} ${obj.unit||''}` : (obj.reference_range ? `${obj.reference_range.min} - ${obj.reference_range.max} ${obj.unit||''}` : '');
        html += `<td tabindex="0">${obj.value} ${obj.unit || ''}<br><span class="${obj.status}">${obj.status || ''}</span><br><span class="ref-range">${ref}</span><br><span class="confidence">${obj.confidence!==undefined ? (obj.confidence*100).toFixed(0)+'%' : ''}</span><br><span class="source">${report.source_file||''}</span></td>`;
      } else {
        html += '<td>-</td>';
      }
    }
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  el.innerHTML = html;
  animateTable();
}

// Toolbar, theme, privacy, and patient selector logic
function exportTableToCSV() {
  const table = document.querySelector('.clinical-table');
  if (!table) return;
  let csv = [];
  for (const row of table.rows) {
    let rowData = [];
    for (const cell of row.cells) {
      rowData.push('"' + cell.innerText.replace(/"/g, '""') + '"');
    }
    csv.push(rowData.join(','));
  }
  const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'biomarker_readings.csv';
  a.click();
  URL.revokeObjectURL(url);
}

document.getElementById('export-csv').onclick = exportTableToCSV;

document.getElementById('print-table').onclick = () => {
  window.print();
};

document.getElementById('upload-json-btn').onclick = () => {
  document.getElementById('upload-json').click();
};
document.getElementById('upload-json').onchange = function(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(evt) {
    try {
      const data = JSON.parse(evt.target.result);
      localStorage.setItem('uploaded_dashboard_data', JSON.stringify(data));
      location.reload();
    } catch (err) {
      alert('Invalid JSON file.');
    }
  };
  reader.readAsText(file);
};

document.getElementById('refresh-btn').onclick = () => {
  localStorage.removeItem('uploaded_dashboard_data');
  location.reload();
};

document.getElementById('privacy-toggle').onchange = function(e) {
  document.body.classList.toggle('anonymize', e.target.checked);
  // Re-render patient snapshot and sidebar
  main();
};

document.getElementById('theme-selector')?.remove();

// Patient selector logic (if multiple patients)
function updatePatientSelector(patients, currentId) {
  const sel = document.getElementById('patient-selector');
  if (patients.length > 1) {
    sel.style.display = '';
    sel.innerHTML = '';
    for (const p of patients) {
      const opt = document.createElement('option');
      opt.value = p.patient_id;
      opt.textContent = p.name;
      sel.appendChild(opt);
    }
    sel.value = currentId;
    sel.onchange = function() {
      localStorage.setItem('selected_patient_id', sel.value);
      location.reload();
    };
  } else {
    sel.style.display = 'none';
  }
}

// Critical alert banner logic
function showAlertBanner(alerts) {
  const banner = document.getElementById('alert-banner');
  const critical = alerts.filter(a => a.severity === 'high' || a.status?.toLowerCase().includes('critical'));
  if (critical.length) {
    banner.textContent = '⚠️ Critical Alert: ' + critical.map(a => a.biomarker + ' - ' + (a.message || a.status)).join(' | ');
    banner.classList.add('active');
  } else {
    banner.classList.remove('active');
    banner.textContent = '';
  }
}

// Clinician notes modal logic
function openNotesModal(notes) {
  const modal = document.getElementById('clinician-notes-modal');
  const textarea = document.getElementById('clinician-notes-text');
  textarea.value = notes || '';
  modal.style.display = 'flex';
}
document.getElementById('close-notes').onclick = () => {
  document.getElementById('clinician-notes-modal').style.display = 'none';
};
document.getElementById('save-notes').onclick = () => {
  const notes = document.getElementById('clinician-notes-text').value;
  localStorage.setItem('clinician_notes', notes);
  document.getElementById('clinician-notes-modal').style.display = 'none';
};

// --- Render Alerts Panel (with Recommendations) ---
function renderAlertsPanel(alerts) {
  const el = document.getElementById('alerts-panel-section');
  if (!el) return;
  el.innerHTML = '<h2 class="section-heading">Alerts & Recommendations</h2>';
  if (!alerts || !alerts.length) {
    el.innerHTML += '<div class="alert">✅ No abnormal or borderline biomarkers detected.</div>';
    return;
  }
  for (const alert of alerts) {
    const div = document.createElement('div');
    div.className = 'alert' + (alert.severity === 'high' ? ' high' : alert.severity === 'borderline' ? ' borderline' : '');
    const emoji = alert.severity === 'high' ? '🔴' : alert.severity === 'borderline' ? '⚠️' : '✅';
    div.innerHTML = `<strong>${emoji} ${alert.biomarker}</strong> <span class="alert-status">${alert.status || ''}</span> <span class="alert-value">${alert.value || ''} ${alert.unit || ''}</span><br><span class="alert-recommendation">${alert.recommendation || ''}</span>`;
    el.appendChild(div);
  }
}

// --- Render Chart Grid (3-column, responsive) ---
function renderChartGrid(trends, dedupedReports) {
  const el = document.getElementById('chart-grid');
  if (!el) return;
  el.innerHTML = '';
  // Find all unique biomarkers
  let allBiomarkers = new Set();
  dedupedReports.forEach(r => Object.keys(r.biomarkers).forEach(b => allBiomarkers.add(b)));
  allBiomarkers = Array.from(allBiomarkers);
  for (const key of allBiomarkers) {
    const values = [];
    const labels = [];
    const units = [];
    const statuses = [];
    const refs = [];
    for (const report of dedupedReports) {
      const biomarkerObj = report.biomarkers[key];
      if (biomarkerObj && typeof biomarkerObj === 'object' && biomarkerObj.value !== undefined) {
        values.push(biomarkerObj.value);
        labels.push(report.report_date);
        units.push(biomarkerObj.unit || '');
        statuses.push(biomarkerObj.status || '');
        refs.push(biomarkerObj.reference_range ? `${biomarkerObj.reference_range.min} - ${biomarkerObj.reference_range.max} ${biomarkerObj.unit || ''}` : '');
      }
    }
    const card = document.createElement('div');
    card.className = 'chart-card';
    card.style.border = '2px solid #FF204E';
    card.style.background = '#fff';
    card.innerHTML = `<h3>${key}</h3><canvas></canvas>`;
    el.appendChild(card);
    const ctx = card.querySelector('canvas').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: key,
          data: values,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,0.08)',
          pointRadius: 5,
          pointBackgroundColor: statuses.map(s => getStatusColor(s)),
          pointBorderColor: '#fff',
          pointHoverRadius: 7,
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: true,
            callbacks: {
              title: ctx => `Date: ${ctx[0].label}`,
              label: ctx => {
                const i = ctx.dataIndex;
                return [
                  `Value: ${ctx.parsed.y} ${units[i]}`,
                  `Status: ${statuses[i]}`,
                  refs[i] ? `Ref: ${refs[i]}` : ''
                ].filter(Boolean);
              }
            }
          },
          title: { display: false }
        },
        interaction: { mode: 'nearest', intersect: false },
        hover: { mode: 'nearest', intersect: false },
        scales: {
          x: { title: { display: true, text: 'Date' } },
          y: { title: { display: true, text: 'Value' }, beginAtZero: false }
        },
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 900, easing: 'easeOutQuart' }
      }
    });
  }
}

// --- Render Trend Cards Sidebar ---
function renderTrendSidebar(dedupedReports) {
  const el = document.getElementById('trend-sidebar');
  if (!el) return;
  el.innerHTML = '<h3 style="margin-bottom:0.7em;">Trends</h3>';
  // For each biomarker, show latest value, trend direction, pill badge
  let allBiomarkers = new Set();
  dedupedReports.forEach(r => Object.keys(r.biomarkers).forEach(b => allBiomarkers.add(b)));
  allBiomarkers = Array.from(allBiomarkers);
  for (const key of allBiomarkers) {
    // Get latest value and trend
    let latest = null, prev = null;
    for (let i = dedupedReports.length - 1; i >= 0; i--) {
      if (dedupedReports[i].biomarkers[key]) {
        if (!latest) latest = dedupedReports[i].biomarkers[key];
        else if (!prev) prev = dedupedReports[i].biomarkers[key];
      }
    }
    const trend = latest && prev ? (latest.value > prev.value ? '↑' : latest.value < prev.value ? '↓' : '→') : '';
    const status = latest?.status || 'Unknown';
    const pillClass = status.toLowerCase();
    const card = document.createElement('div');
    card.className = 'trend-card';
    card.innerHTML = `
      <div class="trend-title">${key}</div>
      <div class="trend-value" style="color:#1a2e22;font-weight:700;">${latest ? latest.value + ' ' + (latest.unit || '') : '-'}</div>
      <span class="trend-pill ${pillClass}">${status} ${trend}</span>
    `;
    card.onclick = () => openTrendModal(key, latest);
    el.appendChild(card);
  }
}

// --- Trend Modal ---
function openTrendModal(biomarker, latest) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.innerHTML = `<div class="modal-content"><span class="close" id="close-trend-modal">&times;</span><h3>${biomarker} Details</h3><p><strong>Latest Value:</strong> ${latest ? latest.value + ' ' + (latest.unit || '') : '-'}</p><p><strong>Status:</strong> ${latest?.status || '-'}</p><p><strong>Reference Range:</strong> ${latest?.reference_range ? latest.reference_range.min + ' - ' + latest.reference_range.max + ' ' + (latest.unit || '') : '-'}</p><p><strong>Description:</strong> Clinical biomarker used for monitoring.</p><p><strong>Complication Risks:</strong> See clinical guidelines.</p><p><strong>Suggested Treatment:</strong> See recommendations above.</p><p><strong>Target Range:</strong> ${latest?.reference_range ? latest.reference_range.min + ' - ' + latest.reference_range.max + ' ' + (latest.unit || '') : '-'}</p></div>`;
  document.body.appendChild(modal);
  document.getElementById('close-trend-modal').onclick = () => modal.remove();
}

// --- Render Tabular Data Panel ---
function renderTabularDataPanel(dedupedReports) {
  const el = document.getElementById('data-table-section');
  if (!el) return;
  let allBiomarkers = new Set();
  dedupedReports.forEach(r => Object.keys(r.biomarkers).forEach(b => allBiomarkers.add(b)));
  allBiomarkers = Array.from(allBiomarkers);
  let html = '<div class="table-scroll"><table class="clinical-table" aria-label="All biomarker readings"><thead><tr><th>Date</th>';
  for (const b of allBiomarkers) html += `<th>${b}</th>`;
  html += '</tr></thead><tbody>';
  for (const report of dedupedReports) {
    html += `<tr><td>${report.report_date}</td>`;
    for (const b of allBiomarkers) {
      const obj = report.biomarkers[b];
      if (obj && typeof obj === 'object' && obj.value !== undefined) {
        html += `<td tabindex="0" class="${obj.status ? obj.status.toLowerCase() : ''}">${obj.value} ${obj.unit || ''}<br><span class="ref-range">${obj.reference_range ? obj.reference_range.min + ' - ' + obj.reference_range.max + ' ' + (obj.unit || '') : ''}</span></td>`;
      } else {
        html += '<td>-</td>';
      }
    }
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  el.innerHTML = html;
  animateTable();
}

// --- Render AI Footer Clinical Summary ---
function renderAIFooterSummary(alerts, dedupedReports) {
  // Compose summary: count normal, borderline, abnormal
  let normal = 0, borderline = 0, abnormal = 0;
  for (const report of dedupedReports) {
    for (const b in report.biomarkers) {
      const s = (report.biomarkers[b].status || '').toLowerCase();
      if (s === 'normal') normal++;
      else if (s === 'borderline') borderline++;
      else if (s === 'high' || s === 'low' || s === 'abnormal') abnormal++;
    }
  }
  const summaryEl = document.getElementById('footer-summary');
  if (!summaryEl) return;
  let summary = `<div class="clinical-summary">
    <strong>Clinical Summary:</strong><br>
    Total status: ✅ ${normal} Normal | ⚠ ${borderline} Borderline | 🔴 ${abnormal} Abnormal<br>
    <ul style="margin:0.7em 0 0 1.2em;">`;
  if (alerts && alerts.length) {
    for (const alert of alerts) {
      const emoji = alert.severity === 'high' ? '🔴' : alert.severity === 'borderline' ? '⚠️' : '✅';
      summary += `<li>${emoji} <strong>${alert.biomarker}</strong> ${alert.status ? alert.status : ''} at ${alert.value || ''} ${alert.unit || ''} → ${alert.recommendation || ''}</li>`;
    }
  }
  summary += '</ul></div>';
  summaryEl.innerHTML = summary;
}

// --- MAIN ---
async function main() {
  let data;
  const uploaded = localStorage.getItem('uploaded_dashboard_data');
  if (uploaded) {
    data = JSON.parse(uploaded);
  } else {
    data = await fetchDashboardData();
  }
  // Multi-patient support
  let patients = [data.patient_profile];
  if (data.patients && Array.isArray(data.patients)) {
    patients = data.patients;
    const selectedId = localStorage.getItem('selected_patient_id') || patients[0].patient_id;
    data.patient_profile = patients.find(p => p.patient_id === selectedId) || patients[0];
    updatePatientSelector(patients, data.patient_profile.patient_id);
  }
  // Deduplicate reports for chart clarity
  const dedupedReports = deduplicateReports(data.patient_profile.reports);
  renderPatientSnapshot(data.patient_profile, dedupedReports);
  renderSummary(data.summary_stats, dedupedReports, data.alerts);
  renderAlertsPanel(data.alerts);
  renderTrendSidebar(dedupedReports);
  renderChartGrid(data.trends, dedupedReports);
  renderTabularDataPanel(dedupedReports);
  renderAIFooterSummary(data.alerts, dedupedReports);
  showAlertBanner(data.alerts || []);
  // Restore theme palette
  const palette = localStorage.getItem('theme_palette');
  if (palette && palette !== 'default') {
    document.getElementById('theme-selector').value = palette;
    document.body.classList.add('theme-' + palette);
  }
  // Restore privacy toggle
  if (document.body.classList.contains('anonymize')) {
    document.getElementById('privacy-toggle').checked = true;
  }
}

main(); 