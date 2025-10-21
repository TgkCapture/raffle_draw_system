document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeAuthMethodToggle();
    initializeUploadForm();
    initializeViewParticipants();
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
    }
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
        });
    }
}

function showNotification(message, type = 'info') {
    // Reuse the same notification function from admin.js
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
        background: ${type === 'success' ? 'var(--success-color)' : 
                      type === 'error' ? 'var(--danger-color)' : 
                      type === 'warning' ? 'var(--warning-color)' : 'var(--info-color)'};
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
            notification.remove();
        }, 300);
    });
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, 5000);
    
    document.body.appendChild(notification);
}

class APIService {
    constructor() {
        this.updateStatus();
        setInterval(() => this.updateStatus(), 10000); // Update every 10 seconds
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/api-config/status');
            const status = await response.json();
            
            document.getElementById('api-status').textContent = 
                status.is_running ? 'RUNNING' : 'STOPPED';
            document.getElementById('api-status').className = 
                status.is_running ? 'status-running' : 'status-stopped';
                
            document.getElementById('start-api-btn').disabled = status.is_running;
            document.getElementById('stop-api-btn').disabled = !status.is_running;
        } catch (error) {
            console.error('Error updating API status:', error);
        }
    }
    
    async startService() {
        try {
            const response = await fetch('/api/api-config/start', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
            this.updateStatus();
        } catch (error) {
            console.error('Error starting API service:', error);
            alert('Error starting API service');
        }
    }
    
    async stopService() {
        try {
            const response = await fetch('/api/api-config/stop', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
            this.updateStatus();
        } catch (error) {
            console.error('Error stopping API service:', error);
            alert('Error stopping API service');
        }
    }
    
    async testConnection() {
        try {
            const response = await fetch('/api/api-config/test', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
        } catch (error) {
            console.error('Error testing API connection:', error);
            alert('Error testing API connection');
        }
    }
}