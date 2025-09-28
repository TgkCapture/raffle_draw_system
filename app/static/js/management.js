// app/static/js/management.js
class RaffleManagement {
    constructor() {
        this.currentDraw = null;
        this.isDrawRunning = false;
        this.updateInterval = null;
        
        this.initializeEventListeners();
        this.loadInitialData();
        this.startAutoUpdate();
    }
    
    initializeEventListeners() {
        // Draw control buttons
        document.getElementById('activate-draw').addEventListener('click', () => this.activateDraw());
        document.getElementById('stop-draw').addEventListener('click', () => this.stopDraw());
        document.getElementById('open-tv-display').addEventListener('click', () => this.openTVDisplay());
        
        // Draw selection
        document.getElementById('draw-select').addEventListener('change', (e) => this.selectDraw(e.target.value));
    }
    
    async loadInitialData() {
        await this.updateDrawsList();
        await this.updateWinners();
        await this.updateStats();
    }
    
    async updateDrawsList() {
        try {
            const response = await fetch('/api/draws');
            const draws = await response.json();
            
            const select = document.getElementById('draw-select');
            select.innerHTML = '<option value="">Select a draw...</option>';
            
            draws.forEach(draw => {
                const option = document.createElement('option');
                option.value = draw.id;
                option.textContent = `${draw.name} - MWK ${draw.prize_amount.toLocaleString()} - ${draw.participant_count} participants`;
                option.dataset.prize = draw.prize_amount;
                option.dataset.winners = draw.number_of_winners;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading draws:', error);
        }
    }
    
    async updateWinners() {
        try {
            const response = await fetch('/api/winners');
            const winners = await response.json();
            
            const table = document.getElementById('winners-table');
            
            if (winners.length === 0) {
                table.innerHTML = '<tr><td colspan="5" class="text-center">No winners yet</td></tr>';
                return;
            }
            
            table.innerHTML = winners.map(winner => `
                <tr>
                    <td>${new Date(winner.won_at).toLocaleDateString()}</td>
                    <td>${winner.phone_number}</td>
                    <td>MWK ${winner.prize_amount.toLocaleString()}</td>
                    <td>${winner.draw_name}</td>
                    <td>${winner.position}${this.getOrdinalSuffix(winner.position)}</td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading winners:', error);
        }
    }
    
    async updateStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            document.getElementById('total-draws').textContent = stats.total_draws;
            document.getElementById('completed-draws').textContent = stats.completed_draws;
            document.getElementById('total-winners').textContent = stats.total_winners;
            document.getElementById('total-prizes').textContent = `MWK ${stats.total_prizes.toLocaleString()}`;
        } catch (error) {
            console.error('Error loading stats:', error);
        }
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
            
            // Update participant count
            const countResponse = await fetch(`/api/participants/count/${drawId}`);
            const countData = await countResponse.json();
            
            document.getElementById('participant-count').textContent = countData.count;
        } catch (error) {
            console.error('Error selecting draw:', error);
        }
    }
    
    updateUI() {
        const activateBtn = document.getElementById('activate-draw');
        const stopBtn = document.getElementById('stop-draw');
        const tvDisplayBtn = document.getElementById('open-tv-display');
        
        if (this.currentDraw) {
            document.getElementById('current-draw-name').textContent = this.currentDraw.name;
            document.getElementById('prize-amount').textContent = `MWK ${this.currentDraw.prize_amount.toLocaleString()}`;
            
            // Calculate remaining winners
            const remainingWinners = this.currentDraw.number_of_winners - (this.currentDraw.winners_drawn || 0);
            document.getElementById('winners-info').textContent = `${remainingWinners} winners remaining`;
            
            activateBtn.disabled = this.isDrawRunning;
            stopBtn.disabled = !this.isDrawRunning;
            tvDisplayBtn.disabled = !this.isDrawRunning;
        } else {
            activateBtn.disabled = true;
            stopBtn.disabled = true;
            tvDisplayBtn.disabled = true;
        }
        
        // Update status badge
        const statusBadge = document.getElementById('draw-status');
        statusBadge.textContent = this.isDrawRunning ? 'Active' : 'Not Active';
        statusBadge.className = `status-badge ${this.isDrawRunning ? 'status-active' : 'status-inactive'}`;
    }
    
    async activateDraw() {
        if (!this.currentDraw) {
            alert('Please select a draw first');
            return;
        }
        
        try {
            const response = await fetch(`/api/draws/${this.currentDraw.id}/start`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isDrawRunning = true;
                this.updateUI();
                alert(data.message);
            } else {
                alert('Error activating draw: ' + data.message);
            }
        } catch (error) {
            console.error('Error activating draw:', error);
            alert('Error activating draw');
        }
    }
    
    async stopDraw() {
        try {
            const response = await fetch('/api/draws/stop', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isDrawRunning = false;
                this.updateUI();
                alert('Draw completed successfully!');
            }
        } catch (error) {
            console.error('Error stopping draw:', error);
        }
    }
    
    openTVDisplay() {
        // Open TV display in new tab
        window.open('/tv', '_blank');
    }
    
    startAutoUpdate() {
        this.updateInterval = setInterval(() => {
            this.updateDrawStatus();
        }, 5000); // Update every 5 seconds
    }
    
    async updateDrawStatus() {
        try {
            const response = await fetch('/api/draws/status');
            const data = await response.json();
            
            if (data.is_running !== this.isDrawRunning) {
                this.isDrawRunning = data.is_running;
                this.updateUI();
            }
        } catch (error) {
            console.error('Error updating draw status:', error);
        }
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
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new RaffleManagement();
});