const tableBody = document.querySelector('#logsTable tbody');
const tableHeadRow = document.querySelector('#logsTable thead tr');
const macFilter = document.getElementById('macFilter');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const refreshBtn = document.getElementById('refreshBtn');

const BASE_COLUMNS = ['mac_address', 'level', 'message', 'created_at'];
const COLUMN_LABELS = {
  mac_address: 'MAC Address',
  level: 'Level',
  message: 'Message',
  created_at: 'Timestamp (UTC)',
};

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

function titleize(column) {
  if (COLUMN_LABELS[column]) {
    return COLUMN_LABELS[column];
  }

  return column
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function deriveColumns(logs) {
  const extras = new Set();
  logs.forEach((log) => {
    Object.keys(log || {}).forEach((key) => {
      if (!BASE_COLUMNS.includes(key)) {
        extras.add(key);
      }
    });
  });

  return [...BASE_COLUMNS, ...Array.from(extras).sort()];
}

function renderHeader(columns) {
  tableHeadRow.innerHTML = '';
  columns.forEach((column) => {
    const th = document.createElement('th');
    th.scope = 'col';
    th.textContent = titleize(column);
    tableHeadRow.appendChild(th);
  });
}

function renderLogs(logs) {
  tableBody.innerHTML = '';
  const columns = logs.length > 0 ? deriveColumns(logs) : [...BASE_COLUMNS];
  renderHeader(columns);

  if (logs.length === 0) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = columns.length;
    cell.className = 'text-center py-4 text-muted';
    cell.textContent = 'No logs found';
    row.appendChild(cell);
    tableBody.appendChild(row);
    return;
  }

  const macAddresses = new Set();

  logs.forEach((log) => {
    if (log.mac_address) {
      macAddresses.add(log.mac_address);
    }
    const row = document.createElement('tr');

    columns.forEach((column) => {
      const cell = document.createElement('td');
      let value = log[column];

      if (column === 'mac_address') {
        const code = document.createElement('code');
        code.textContent = value == null ? '' : String(value);
        cell.appendChild(code);
      } else if (column === 'created_at') {
        if (value) {
          const primary = document.createElement('div');
          primary.textContent = new Date(value).toLocaleString();
          const secondary = document.createElement('small');
          secondary.className = 'text-muted';
          secondary.textContent = value;
          cell.appendChild(primary);
          cell.appendChild(document.createElement('br'));
          cell.appendChild(secondary);
        }
      } else {
        if (value === null || value === undefined) {
          value = '';
        } else if (typeof value === 'object') {
          value = JSON.stringify(value);
        }
        cell.textContent = String(value);
      }

      row.appendChild(cell);
    });

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
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    const columnCount = tableHeadRow.children.length || BASE_COLUMNS.length;
    cell.colSpan = columnCount;
    cell.className = 'text-center text-danger py-4';
    cell.textContent = 'Failed to load logs';
    row.appendChild(cell);
    tableBody.innerHTML = '';
    tableBody.appendChild(row);
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
