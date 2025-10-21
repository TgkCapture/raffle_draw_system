// static/js/participants.js
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeAuthMethodToggle();
    initializeUploadForm();
    initializeViewParticipants();
    initializeAPIConfig();
    
    // Initialize API service
    window.apiService = new APIService();
});

function initializeTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const subtabId = this.getAttribute('data-subtab');
            
            // Update active tab
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding content
            document.querySelectorAll('.subtab-content').forEach(content => {
                content.classList.remove('active');
                if (content.id === subtabId) {
                    content.classList.add('active');
                }
            });
        });
    });
}

function initializeAuthMethodToggle() {
    const authMethodSelect = document.getElementById('auth-method');
    const tokenField = document.getElementById('token-field');
    
    if (authMethodSelect && tokenField) {
        authMethodSelect.addEventListener('change', function() {
            tokenField.style.display = this.value === 'none' ? 'none' : 'block';
        });
        
        // Trigger change event to set initial state
        authMethodSelect.dispatchEvent(new Event('change'));
    }
}

function initializeAPIConfig() {
    const apiConfigForm = document.getElementById('api-config-form');
    if (apiConfigForm) {
        apiConfigForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveAPIConfig();
        });
    }
    
    const startApiBtn = document.getElementById('start-api-btn');
    const stopApiBtn = document.getElementById('stop-api-btn');
    const testApiBtn = document.getElementById('test-api');
    const testConnectionBtn = document.getElementById('test-connection-btn');
    
    if (startApiBtn) {
        startApiBtn.addEventListener('click', function() {
            window.apiService.startService();
        });
    }
    
    if (stopApiBtn) {
        stopApiBtn.addEventListener('click', function() {
            window.apiService.stopService();
        });
    }
    
    if (testApiBtn) {
        testApiBtn.addEventListener('click', function() {
            window.apiService.testConnection();
        });
    }
    
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', function() {
            window.apiService.testConnection();
        });
    }
}

function saveAPIConfig() {
    const config = {
        endpoint_url: document.getElementById('api-endpoint').value,
        auth_method: document.getElementById('auth-method').value,
        api_key: document.getElementById('api-token').value,
        refresh_interval: parseInt(document.getElementById('refresh-interval').value),
        is_active: document.getElementById('api-active').checked,
        default_draw_id: document.getElementById('default-draw').value || null
    };
    
    // Validate required fields
    if (!config.endpoint_url) {
        showNotification('API Endpoint URL is required', 'error');
        return;
    }
    
    fetch('/api/api-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('API configuration saved successfully', 'success');
        } else {
            showNotification('Error saving API configuration: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error saving API configuration', 'error');
    });
}

function initializeUploadForm() {
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('participant-file');
            const drawSelect = document.getElementById('draw-select');
            
            if (!fileInput.files[0]) {
                showNotification('Please select a file to upload', 'error');
                return;
            }
            
            if (!drawSelect.value) {
                showNotification('Please select a draw', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('draw_id', drawSelect.value);
            
            // Show loading state
            const submitBtn = uploadForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Uploading...';
            submitBtn.disabled = true;
            
            fetch('/api/participants/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message, 'success');
                    uploadForm.reset();
                    
                    // Refresh participants list if we're on the view tab
                    const viewDrawSelect = document.getElementById('view-draw-select');
                    if (viewDrawSelect && viewDrawSelect.value) {
                        loadParticipants(viewDrawSelect.value);
                    }
                } else {
                    showNotification(data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error uploading file', 'error');
            })
            .finally(() => {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            });
        });
    }
}

function initializeViewParticipants() {
    const viewDrawSelect = document.getElementById('view-draw-select');
    if (viewDrawSelect) {
        viewDrawSelect.addEventListener('change', function() {
            const drawId = this.value;
            loadParticipants(drawId);
        });
    }
}

function loadParticipants(drawId) {
    if (!drawId) {
        const table = document.getElementById('participants-table');
        table.innerHTML = '<tr><td colspan="4" class="text-center">Select a draw to view participants</td></tr>';
        return;
    }
    
    // Show loading state
    const table = document.getElementById('participants-table');
    table.innerHTML = '<tr><td colspan="4" class="text-center">Loading participants...</td></tr>';
    
    fetch(`/api/participants/${drawId}`)
        .then(response => response.json())
        .then(participants => {
            if (participants.length === 0) {
                table.innerHTML = '<tr><td colspan="4" class="text-center">No participants found</td></tr>';
                return;
            }
            
            table.innerHTML = participants.map(p => `
                <tr>
                    <td>${p.phone_number}</td>
                    <td>${new Date(p.added_at).toLocaleDateString()}</td>
                    <td>${p.source}</td>
                    <td><span class="status-badge ${p.is_verified ? 'status-active' : 'status-inactive'}">${p.is_verified ? 'Verified' : 'Pending'}</span></td>
                </tr>
            `).join('');
        })
        .catch(error => {
            console.error('Error:', error);
            table.innerHTML = '<tr><td colspan="4" class="text-center">Error loading participants</td></tr>';
        });
}

function showNotification(message, type = 'info') {
    // Remove any existing notifications
    document.querySelectorAll('.notification').forEach(notification => {
        notification.remove();
    });
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        </div>
    `;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : 
                      type === 'error' ? '#dc3545' : 
                      type === 'warning' ? '#ffc107' : '#17a2b8'};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
        max-width: 400px;
    `;
    
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    });
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
    
    document.body.appendChild(notification);
}

class APIService {
    constructor() {
        this.updateStatus();
        // Update status every 10 seconds
        setInterval(() => this.updateStatus(), 10000);
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/api-config/status');
            const status = await response.json();
            
            const statusElement = document.getElementById('api-status');
            const startBtn = document.getElementById('start-api-btn');
            const stopBtn = document.getElementById('stop-api-btn');
            
            if (statusElement) {
                statusElement.textContent = status.is_running ? 'RUNNING' : 'STOPPED';
                statusElement.className = status.is_running ? 'status-running' : 'status-stopped';
            }
            
            if (startBtn) startBtn.disabled = status.is_running;
            if (stopBtn) stopBtn.disabled = !status.is_running;
            
        } catch (error) {
            console.error('Error updating API status:', error);
        }
    }
    
    async startService() {
        try {
            const response = await fetch('/api/api-config/start', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
            } else {
                showNotification(result.message, 'error');
            }
            
            this.updateStatus();
        } catch (error) {
            console.error('Error starting API service:', error);
            showNotification('Error starting API service', 'error');
        }
    }
    
    async stopService() {
        try {
            const response = await fetch('/api/api-config/stop', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
            } else {
                showNotification(result.message, 'error');
            }
            
            this.updateStatus();
        } catch (error) {
            console.error('Error stopping API service:', error);
            showNotification('Error stopping API service', 'error');
        }
    }
    
    async testConnection() {
        try {
            const response = await fetch('/api/api-config/test', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
            } else {
                showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error testing API connection:', error);
            showNotification('Error testing API connection', 'error');
        }
    }
}