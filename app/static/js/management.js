class RaffleManagement {
    constructor() {
        this.currentDraw = null;
        this.isDrawRunning = false;
        this.drawStatus = 'inactive'; // inactive, active, paused, completed
        this.statusUpdateInterval = null;
        this.winnersUpdateInterval = null;
        this.lastWinnerUpdate = null;
        
        this.initializeEventListeners();
        this.loadInitialData();
        this.startAutoUpdate();
        this.startWinnersAutoRefresh();
    }
    
    initializeEventListeners() {
        // Draw control buttons
        document.getElementById('activate-draw').addEventListener('click', () => this.activateDraw());
        document.getElementById('stop-draw').addEventListener('click', () => this.stopDraw());
        document.getElementById('pause-draw').addEventListener('click', () => this.pauseDraw());
        document.getElementById('open-tv-display').addEventListener('click', () => this.openTVDisplay());
        
        // Refresh buttons
        document.getElementById('refresh-status').addEventListener('click', () => this.refreshStatus());
        document.getElementById('refresh-winners').addEventListener('click', () => this.updateWinners());
        
        // Draw selection
        document.getElementById('draw-select').addEventListener('change', (e) => this.selectDraw(e.target.value));
        
        // Real-time updates using EventSource for winner notifications
        this.setupRealTimeUpdates();
    }
    
    setupRealTimeUpdates() {
        // Use EventSource for server-sent events if supported
        if (typeof(EventSource) !== "undefined") {
            const eventSource = new EventSource('/api/events');
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'winner_drawn') {
                    this.showWinnerNotification(data.winner);
                    this.updateWinners(); // Immediately update winners list
                    this.updateStats();
                    this.updateDrawStatus();
                } else if (data.type === 'draw_status_changed') {
                    this.updateDrawStatus();
                    this.updateDrawsList();
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('EventSource error:', error);
            };
        }
    }
    
    async loadInitialData() {
        await this.updateDrawsList();
        await this.updateWinners();
        await this.updateStats();
        await this.updateDrawStatus();
    }
    
    async updateDrawsList() {
        try {
            const response = await fetch('/api/draws');
            const draws = await response.json();
            
            const select = document.getElementById('draw-select');
            const currentValue = select.value;
            
            select.innerHTML = '<option value="">Select a draw...</option>';
            
            draws.forEach(draw => {
                const option = document.createElement('option');
                option.value = draw.id;
                
                let statusText = '';
                if (draw.status === 'active') statusText = ' (ACTIVE)';
                else if (draw.status === 'completed') statusText = ' (COMPLETED)';
                
                option.textContent = `${draw.name} - MWK ${draw.prize_amount.toLocaleString()} - ${draw.participant_count || 0} participants${statusText}`;
                option.dataset.prize = draw.prize_amount;
                option.dataset.winners = draw.number_of_winners;
                option.dataset.status = draw.status;
                
                // Highlight active draws
                if (draw.status === 'active') {
                    option.style.fontWeight = 'bold';
                    option.style.color = '#28a745';
                }
                
                select.appendChild(option);
            });
            
            // Restore previous selection if still valid
            if (currentValue) {
                select.value = currentValue;
            }
        } catch (error) {
            console.error('Error loading draws:', error);
        }
    }
    
    async updateWinners() {
        try {
            const response = await fetch('/api/winners?limit=20');
            const winners = await response.json();
            
            const table = document.getElementById('winners-table');
            
            if (winners.length === 0) {
                table.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No winners yet</td></tr>';
                return;
            }
            
            table.innerHTML = winners.map(winner => `
                <tr class="${winner.is_new ? 'table-success' : ''}">
                    <td>${new Date(winner.won_at).toLocaleString()}</td>
                    <td>
                        <strong>${winner.phone_number}</strong>
                        ${winner.is_new ? '<span class="badge bg-success ms-2">NEW</span>' : ''}
                    </td>
                    <td>MWK ${winner.prize_amount.toLocaleString()}</td>
                    <td>${winner.draw_name}</td>
                    <td>
                        <span class="badge bg-primary">${winner.position}${this.getOrdinalSuffix(winner.position)}</span>
                    </td>
                    <td>
                        <span class="badge bg-success">Confirmed</span>
                    </td>
                </tr>
            `).join('');
            
            // Remove new highlights after 5 seconds
            setTimeout(() => {
                document.querySelectorAll('.table-success').forEach(row => {
                    row.classList.remove('table-success');
                });
            }, 5000);
            
        } catch (error) {
            console.error('Error loading winners:', error);
        }
    }
    
    async updateStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            document.getElementById('total-draws').textContent = stats.total_draws;
            document.getElementById('active-draws').textContent = stats.active_draws;
            document.getElementById('completed-draws').textContent = stats.completed_draws;
            document.getElementById('total-winners').textContent = stats.total_winners;
            document.getElementById('total-prizes').textContent = `MWK ${stats.total_prizes.toLocaleString()}`;
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    async updateDrawStatus() {
        try {
            const response = await fetch('/api/draws/status');
            const data = await response.json();
            
            this.isDrawRunning = data.is_running;
            this.drawStatus = data.status;
            this.currentDraw = data.current_draw;
            
            this.updateStatusUI(data);
            
            // Update current draw info if there's an active draw
            if (data.current_draw) {
                await this.updateCurrentDrawInfo(data.current_draw);
            } else {
                // Reset display when no active draw
                document.getElementById('current-draw-name').textContent = 'No active draw';
                document.getElementById('participant-count').textContent = '0';
                document.getElementById('prize-amount').textContent = 'MWK 0';
                document.getElementById('winners-progress').textContent = '0 winners drawn';
            }
            
        } catch (error) {
            console.error('Error updating draw status:', error);
        }
    }
    
    async updateCurrentDrawInfo(drawId) {
        try {
            const response = await fetch(`/api/draws/${drawId}`);
            const draw = await response.json();
            
            document.getElementById('current-draw-name').textContent = draw.name;
            document.getElementById('prize-amount').textContent = `MWK ${draw.prize_amount.toLocaleString()}`;
            
            // Update participant count
            const countResponse = await fetch(`/api/participants/count/${drawId}`);
            const countData = await countResponse.json();
            document.getElementById('participant-count').textContent = countData.count;
            
            // Update winners progress - FIXED: Get actual winners drawn count
            const winnersDrawn = draw.winners_drawn || 0;
            const totalWinners = draw.number_of_winners;
            
            document.getElementById('winners-progress').textContent = 
                `${winnersDrawn} of ${totalWinners} winners drawn`;
            
        } catch (error) {
            console.error('Error updating current draw info:', error);
        }
    }
    
    updateStatusUI(statusData) {
        const statusLight = document.getElementById('status-light');
        const statusText = document.getElementById('draw-status-text');
        const activateBtn = document.getElementById('activate-draw');
        const pauseBtn = document.getElementById('pause-draw');
        const stopBtn = document.getElementById('stop-draw');
        const tvDisplayBtn = document.getElementById('open-tv-display');
        
        // Update status indicator
        if (statusData.is_running) {
            statusLight.className = 'status-light active';
            statusText.textContent = `Draw Active - ${statusData.current_draw_name}`;
            statusText.style.color = '#28a745';
        } else if (statusData.status === 'paused') {
            statusLight.className = 'status-light paused';
            statusText.textContent = 'Draw Paused';
            statusText.style.color = '#ffc107';
        } else {
            statusLight.className = 'status-light';
            statusText.textContent = 'No Active Draw';
            statusText.style.color = '#6c757d';
        }
        
        // Update button states
        const hasActiveDraw = statusData.is_running;
        const hasSelectedDraw = this.currentDraw && this.currentDraw.status === 'draft';
        
        activateBtn.disabled = hasActiveDraw || !hasSelectedDraw;
        pauseBtn.disabled = !hasActiveDraw;
        stopBtn.disabled = !hasActiveDraw;
        tvDisplayBtn.disabled = !hasActiveDraw;
        
        // Update select dropdown to reflect current active draw
        const select = document.getElementById('draw-select');
        Array.from(select.options).forEach(option => {
            if (option.value == statusData.current_draw) {
                option.textContent = option.textContent.replace(' (ACTIVE)', '') + ' (ACTIVE)';
                option.style.fontWeight = 'bold';
                option.style.color = '#28a745';
            } else if (option.textContent.includes('(ACTIVE)')) {
                option.textContent = option.textContent.replace(' (ACTIVE)', '');
                option.style.fontWeight = 'normal';
                option.style.color = '';
            }
        });
    }
    
    async selectDraw(drawId) {
        if (!drawId) {
            this.currentDraw = null;
            this.updateUI();
            return;
        }
        
        try {
            const response = await fetch(`/api/draws/${drawId}`);
            const draw = await response.json();
            
            this.currentDraw = draw;
            this.updateUI();
            
        } catch (error) {
            console.error('Error selecting draw:', error);
        }
    }
    
    updateUI() {
        // This method now primarily handles the draw selection UI
        const activateBtn = document.getElementById('activate-draw');
        
        if (this.currentDraw) {
            const canActivate = !this.isDrawRunning && this.currentDraw.status === 'draft';
            activateBtn.disabled = !canActivate;
        } else {
            activateBtn.disabled = true;
        }
    }
    
    async activateDraw() {
        if (!this.currentDraw) {
            this.showAlert('Please select a draw first', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`/api/draws/${this.currentDraw.id}/start`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Draw activated successfully!', 'success');
                await this.updateDrawStatus();
                await this.updateDrawsList();
            } else {
                this.showAlert('Error activating draw: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('Error activating draw:', error);
            this.showAlert('Error activating draw', 'error');
        }
    }
    
    async pauseDraw() {
        try {
            const response = await fetch('/api/draws/pause', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Draw paused', 'info');
                await this.updateDrawStatus();
            }
        } catch (error) {
            console.error('Error pausing draw:', error);
            this.showAlert('Error pausing draw', 'error');
        }
    }
    
    async stopDraw() {
        if (!confirm('Are you sure you want to complete this draw? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch('/api/draws/stop', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Draw completed successfully!', 'success');
                await this.updateDrawStatus();
                await this.updateDrawsList();
                await this.updateWinners();
                await this.updateStats();
            }
        } catch (error) {
            console.error('Error stopping draw:', error);
            this.showAlert('Error completing draw', 'error');
        }
    }
    
    openTVDisplay() {
        window.open('/tv', '_blank', 'width=1200,height=800');
    }
    
    async refreshStatus() {
        await this.updateDrawStatus();
        await this.updateDrawsList();
        this.showAlert('Status refreshed', 'info');
    }
    
    startAutoUpdate() {
        // Update status every 10 seconds
        this.statusUpdateInterval = setInterval(() => {
            this.updateDrawStatus();
            this.updateStats();
        }, 10000);
    }
    
    startWinnersAutoRefresh() {
        // Update winners every 2 seconds
        this.winnersUpdateInterval = setInterval(() => {
            this.updateWinners();
        }, 2000);
    }
    
    showWinnerNotification(winner) {
        // Create a toast notification for new winners
        const toast = document.createElement('div');
        toast.className = 'position-fixed top-0 end-0 p-3';
        toast.style.zIndex = '9999';
        
        toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header bg-success text-white">
                    <strong class="me-auto">New Winner!</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    <strong>${winner.phone_number}</strong><br>
                    ${winner.draw_name} - ${winner.position}${this.getOrdinalSuffix(winner.position)} winner<br>
                    <small>MWK ${winner.prize_amount.toLocaleString()}</small>
                </div>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    showAlert(message, type = 'info') {
        // Simple alert implementation - you might want to use a proper toast library
        alert(`${type.toUpperCase()}: ${message}`);
    }
    
    getOrdinalSuffix(number) {
        if (number % 100 >= 11 && number % 100 <= 13) return 'th';
        switch (number % 10) {
            case 1: return 'st';
            case 2: return 'nd';
            case 3: return 'rd';
            default: return 'th';
        }
    }

    // Clean up intervals when page is unloaded
    destroy() {
        if (this.statusUpdateInterval) {
            clearInterval(this.statusUpdateInterval);
        }
        if (this.winnersUpdateInterval) {
            clearInterval(this.winnersUpdateInterval);
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    const management = new RaffleManagement();
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        management.destroy();
    });
});