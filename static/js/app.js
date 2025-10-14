const tableBody = document.querySelector('#logsTable tbody');
const macFilter = document.getElementById('macFilter');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const refreshBtn = document.getElementById('refreshBtn');

async function fetchLogs() {
  const [sortField, sortOrder] = sortSelect.value.split(':');
  const params = new URLSearchParams();

  if (macFilter.value) {
    params.append('mac', macFilter.value);
  }
  if (searchInput.value) {
    params.append('search', searchInput.value);
  }
  params.append('sort', sortField);
  params.append('order', sortOrder);

  const query = params.toString();
  const response = await axios.get(query ? `/api/logs?${query}` : '/api/logs');
  return response.data.logs;
}

function renderLogs(logs) {
  tableBody.innerHTML = '';
  if (logs.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center py-4 text-muted">No logs found</td>
      </tr>`;
    return;
  }

  const macAddresses = new Set();

  logs.forEach((log) => {
    macAddresses.add(log.mac_address);
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><code>${log.mac_address}</code></td>
      <td>${log.level ?? ''}</td>
      <td>${log.message}</td>
      <td>${new Date(log.created_at).toLocaleString()}<br /><small class="text-muted">${log.created_at}</small></td>
    `;
    tableBody.appendChild(row);
  });

  updateMacFilter(Array.from(macAddresses).sort());
}

function updateMacFilter(macAddresses) {
  const currentValue = macFilter.value;
  macFilter.options.length = 1; // Preserve the "All" option

  macAddresses.forEach((mac) => {
    const option = document.createElement('option');
    option.value = mac;
    option.textContent = mac;
    macFilter.appendChild(option);
  });

  const hasCurrent = macAddresses.includes(currentValue);
  macFilter.value = hasCurrent ? currentValue : '';
}

async function refreshLogs() {
  try {
    const logs = await fetchLogs();
    renderLogs(logs);
  } catch (error) {
    console.error('Failed to load logs', error);
    tableBody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-danger py-4">Failed to load logs</td>
      </tr>`;
  }
}

refreshBtn.addEventListener('click', refreshLogs);

searchInput.addEventListener('input', () => {
  refreshLogs();
});

sortSelect.addEventListener('change', () => {
  refreshLogs();
});

macFilter.addEventListener('change', () => {
  refreshLogs();
});

refreshLogs();
