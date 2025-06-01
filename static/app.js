// Global variables
let authToken = localStorage.getItem('authToken');
let currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
    setupEventListeners();
    setDefaultDates();
});

function checkAuthStatus() {
    if (authToken && currentUser) {
        showDashboard();
        updateUserInfo();
        loadProfile();
        if (currentUser.role === 'admin') {
            document.getElementById('adminSection').style.display = 'block';
            loadAnalyticsSummary();
            loadTopCustomers();
        }
    } else {
        showAuth();
    }
}

function setupEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await login();
    });

    // Register form
    document.getElementById('registerForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await register();
    });

    // Upload form
    document.getElementById('uploadForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await uploadCSV();
    });

    // Compression forms
    document.getElementById('compressForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await compressString();
    });

    document.getElementById('decompressForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await decompressString();
    });
}

function setDefaultDates() {
    const today = new Date();
    const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    document.getElementById('fromDate').value = lastWeek.toISOString().split('T')[0];
    document.getElementById('toDate').value = today.toISOString().split('T')[0];
}

function showAuth() {
    document.getElementById('authSection').style.display = 'block';
    document.getElementById('dashboardSection').style.display = 'none';
    document.getElementById('userInfo').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
}

function showDashboard() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('dashboardSection').style.display = 'block';
    document.getElementById('userInfo').style.display = 'inline';
    document.getElementById('logoutBtn').style.display = 'inline-block';
}

function updateUserInfo() {
    if (currentUser) {
        document.getElementById('username').textContent = currentUser.username;
        document.getElementById('userRole').textContent = currentUser.role;
    }
}

async function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            currentUser = data.user;
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            showAlert('Login successful!', 'success');
            showDashboard();
            updateUserInfo();
            loadProfile();
            
            if (currentUser.role === 'admin') {
                document.getElementById('adminSection').style.display = 'block';
                loadAnalyticsSummary();
                loadTopCustomers();
            }
        } else {
            showAlert(data.detail || 'Login failed', 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

async function register() {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;
    const role = document.getElementById('registerRole').value;

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password, role }),
        });

        const data = await response.json();

        if (response.ok) {
            showAlert('Registration successful! Please login.', 'success');
            // Switch to login tab
            document.querySelector('[href="#loginTab"]').click();
            document.getElementById('registerForm').reset();
        } else {
            showAlert(data.detail || 'Registration failed', 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    
    showAuth();
    showAlert('Logged out successfully', 'info');
}

async function loadProfile() {
    if (!authToken) return;

    try {
        const response = await fetch('/api/profile', {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        const data = await response.json();

        if (response.ok) {
            const profileInfo = document.getElementById('profileInfo');
            profileInfo.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <strong>ID:</strong> ${data.id}<br>
                        <strong>Username:</strong> ${data.username}<br>
                        <strong>Role:</strong> <span class="badge bg-${data.role === 'admin' ? 'warning' : 'info'}">${data.role}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Created:</strong> ${new Date(data.created_at).toLocaleString()}
                    </div>
                </div>
            `;
        } else {
            showAlert('Failed to load profile', 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

async function uploadCSV() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        showAlert('Please select a CSV file', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload-sales', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
            body: formData,
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(`Successfully uploaded ${data.records_count} sales records`, 'success');
            fileInput.value = '';
            // Refresh analytics data
            loadAnalyticsSummary();
            loadTopCustomers();
        } else {
            showAlert(data.detail || 'Upload failed', 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

async function loadAnalyticsSummary() {
    if (!authToken || currentUser.role !== 'admin') return;

    try {
        const response = await fetch('/api/analytics/summary', {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        const data = await response.json();

        if (response.ok) {
            const summaryDiv = document.getElementById('analyticsSummary');
            summaryDiv.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">$${data.total_sales.toLocaleString()}</div>
                        <div class="stat-label">Total Sales</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.total_transactions}</div>
                        <div class="stat-label">Transactions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">$${data.average_order_value.toFixed(2)}</div>
                        <div class="stat-label">Avg Order</div>
                    </div>
                </div>
            `;
        } else {
            showAlert('Failed to load analytics summary', 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

async function loadTopCustomers() {
    if (!authToken || currentUser.role !== 'admin') return;

    const limit = document.getElementById('customerLimit').value;

    try {
        const response = await fetch(`/api/analytics/top-customers?limit=${limit}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        const data = await response.json();

        if (response.ok) {
            const customersDiv = document.getElementById('topCustomers');
            if (data.length === 0) {
                customersDiv.innerHTML = '<p class="text-muted">No customer data available</p>';
            } else {
                customersDiv.innerHTML = `
                    <div class="customer-list">
                        ${data.map((customer, index) => `
                            <div class="d-flex justify-content-between align-items-center mb-2 p-2 bg-secondary rounded">
                                <div>
                                    <strong>${index + 1}. ${customer.customer_name}</strong><br>
                                    <small>${customer.transaction_count} transactions</small>
                                </div>
                                <div class="text-end">
                                    <span class="text-success">$${customer.total_sales.toLocaleString()}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
        } else {
            showAlert('Failed to load top customers', 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

async function loadSalesByDate() {
    if (!authToken || currentUser.role !== 'admin') return;

    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;

    if (!fromDate || !toDate) {
        showAlert('Please select both from and to dates', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/analytics/by-date?from=${fromDate}&to=${toDate}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        const data = await response.json();

        if (response.ok) {
            const salesDiv = document.getElementById('salesByDate');
            if (data.length === 0) {
                salesDiv.innerHTML = '<p class="text-muted">No sales data found for the selected date range</p>';
            } else {
                salesDiv.innerHTML = `
                    <div class="sales-list">
                        <div class="table-responsive">
                            <table class="table table-sm table-dark">
                                <thead>
                                    <tr>
                                        <th>Customer</th>
                                        <th>Amount</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.map(sale => `
                                        <tr>
                                            <td>${sale.customer_name}</td>
                                            <td>$${sale.amount.toFixed(2)}</td>
                                            <td>${new Date(sale.date).toLocaleDateString()}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        <small class="text-muted">${data.length} records found</small>
                    </div>
                `;
            }
        } else {
            showAlert('Failed to load sales data', 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

async function compressString() {
    const text = document.getElementById('textToCompress').value;

    if (!text.trim()) {
        showAlert('Please enter text to compress', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/compress-string', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text }),
        });

        const data = await response.json();

        if (response.ok) {
            const resultDiv = document.getElementById('compressionResult');
            resultDiv.innerHTML = `
                <div class="compress-result">
                    <h6>Compression Result</h6>
                    <p><strong>Original Size:</strong> ${data.original_size} bytes</p>
                    <p><strong>Compressed Size:</strong> ${data.compressed_size} bytes</p>
                    <p><strong>Compression Ratio:</strong> ${data.compression_ratio}%</p>
                    <div class="mb-2">
                        <label class="form-label">Compressed Data (Base64):</label>
                        <textarea class="form-control" rows="3" readonly>${data.compressed_data}</textarea>
                    </div>
                    <button class="btn btn-sm btn-secondary" onclick="copyToClipboard('${data.compressed_data}')">
                        <i class="fas fa-copy"></i> Copy Compressed Data
                    </button>
                </div>
            `;
        } else {
            showAlert('Compression failed: ' + data.detail, 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

async function decompressString() {
    const compressedData = document.getElementById('compressedData').value;

    if (!compressedData.trim()) {
        showAlert('Please enter compressed data to decompress', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/decompress-string', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(compressedData.trim()),
        });

        const data = await response.json();

        if (response.ok) {
            const resultDiv = document.getElementById('decompressionResult');
            resultDiv.innerHTML = `
                <div class="compress-result">
                    <h6>Decompression Result</h6>
                    <p><strong>Original Size:</strong> ${data.original_size} bytes</p>
                    <div class="mb-2">
                        <label class="form-label">Decompressed Text:</label>
                        <textarea class="form-control" rows="5" readonly>${data.decompressed_text}</textarea>
                    </div>
                </div>
            `;
        } else {
            showAlert('Decompression failed: ' + data.detail, 'danger');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'danger');
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Compressed data copied to clipboard!', 'success');
    }).catch(() => {
        showAlert('Failed to copy to clipboard', 'danger');
    });
}

function showAlert(message, type) {
    const alertContainer = document.getElementById('alertContainer');
    const alertId = 'alert-' + Date.now();
    
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHTML);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, 5000);
}
