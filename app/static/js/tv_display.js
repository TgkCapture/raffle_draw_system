// static/js/tv_display.js
class RaffleDrawTV {
    constructor() {
        this.isDrawing = false;
        this.animationInterval = null;
        this.currentWinners = [];
        this.totalWinners = 0;
        this.winnersDrawn = 0;
        this.currentDraw = null;
        this.isDrawingInProgress = false;
        
        this.initializeEventListeners();
        this.updateDrawStatus();
        this.startStatusUpdates();
    }
    
    initializeEventListeners() {
        document.getElementById('tv-draw-winner').addEventListener('click', () => this.drawWinner());
        document.getElementById('tv-stop-draw').addEventListener('click', () => this.stopDraw());
        
        // Double click to exit TV mode (for admin)
        document.addEventListener('dblclick', () => {
            window.location.href = '/';
        });
    }
    
    async updateDrawStatus() {
        try {
            const response = await fetch('/api/draws/status');
            const data = await response.json();
            
            if (data.is_running) {
                this.isDrawing = true;
                this.totalWinners = data.total_winners;
                this.winnersDrawn = data.winners_drawn;
                this.updateUIForActiveDraw();
                this.updateProgressInfo();
                
                // Get current draw info
                const drawsResponse = await fetch('/api/draws');
                const draws = await drawsResponse.json();
                this.currentDraw = draws.find(d => d.id === data.current_draw);
                this.updateDrawInfo();
                
                // Load existing winners
                await this.loadExistingWinners();
            } else {
                this.isDrawing = false;
                this.updateUIForInactiveDraw();
            }
        } catch (error) {
            console.error('Error updating draw status:', error);
        }
    }
    
    async loadExistingWinners() {
        try {
            const response = await fetch('/api/winners');
            const winners = await response.json();
            
            // Filter winners for current draw
            this.currentWinners = winners.filter(winner => 
                winner.draw_name === this.currentDraw.name
            ).sort((a, b) => a.position - b.position);
            
            this.updateWinnersList();
        } catch (error) {
            console.error('Error loading existing winners:', error);
        }
    }
    
    async drawWinner() {
        if (!this.isDrawing || this.isDrawingInProgress) return;
        
        this.isDrawingInProgress = true;
        document.getElementById('tv-draw-winner').disabled = true;
        
        try {
            // Start 10-second animation
            await this.startAnimation(10000); // 10 seconds
            
            const response = await fetch('/api/draws/draw-winner', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success && data.winner) {
                this.displayWinner(data.winner);
                this.currentWinners.push(data.winner);
                this.winnersDrawn = data.winner.position;
                this.totalWinners = data.winner.total_winners;
                
                this.updateProgressInfo();
                this.updateWinnersList();
                
                // If draw is complete, show complete button
                if (data.winner.draw_complete) {
                    document.getElementById('tv-stop-draw').classList.remove('hidden');
                    document.getElementById('tv-draw-winner').classList.add('hidden');
                } else {
                    // Re-enable draw button after 3 seconds
                    setTimeout(() => {
                        document.getElementById('tv-draw-winner').disabled = false;
                    }, 3000);
                }
            } else {
                this.showNotification('Error drawing winner: ' + data.message, 'error');
                document.getElementById('tv-draw-winner').disabled = false;
            }
        } catch (error) {
            console.error('Error drawing winner:', error);
            this.showNotification('Error drawing winner', 'error');
            document.getElementById('tv-draw-winner').disabled = false;
        } finally {
            this.isDrawingInProgress = false;
        }
    }
    
    async startAnimation(duration = 10000) {
        const numberDisplay = document.getElementById('number-display');
        numberDisplay.classList.add('spinning');
        numberDisplay.textContent = 'DRAWING...';
        
        try {
            const response = await fetch('/api/draws/animation');
            const data = await response.json();
            
            if (data.success && data.sequence.length > 0) {
                const startTime = Date.now();
                let index = 0;
                
                this.animationInterval = setInterval(() => {
                    const elapsed = Date.now() - startTime;
                    
                    if (elapsed >= duration) {
                        this.stopAnimation();
                        return;
                    }
                    
                    if (index < data.sequence.length) {
                        numberDisplay.textContent = data.sequence[index].phone_number;
                        index++;
                    } else {
                        // Loop through the sequence if we reach the end before duration
                        index = 0;
                    }
                }, 80); // Update every 80ms for smooth animation
            }
        } catch (error) {
            console.error('Error getting animation:', error);
            // Fallback: just show "DRAWING..." for the duration
            setTimeout(() => {
                this.stopAnimation();
            }, duration);
        }
    }
    
    stopAnimation() {
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
            this.animationInterval = null;
        }
        
        const numberDisplay = document.getElementById('number-display');
        numberDisplay.classList.remove('spinning');
    }
    
    displayWinner(winner) {
        this.stopAnimation();
        
        const numberDisplay = document.getElementById('number-display');
        const winnerDisplay = document.getElementById('winner-display');
        
        numberDisplay.classList.add('hidden');
        winnerDisplay.classList.remove('hidden');
        winnerDisplay.textContent = winner.phone_number;
        winnerDisplay.classList.add('pulse');
        
        // Create confetti effect
        this.createConfetti();
    }
    
    async stopDraw() {
        try {
            const response = await fetch('/api/draws/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isDrawing = false;
                this.showNotification('Draw completed successfully!', 'success');
                this.updateUIForInactiveDraw();
            }
        } catch (error) {
            console.error('Error stopping draw:', error);
            this.showNotification('Error completing draw', 'error');
        }
    }
    
    updateUIForActiveDraw() {
        document.getElementById('tv-draw-winner').classList.remove('hidden');
        document.getElementById('tv-draw-winner').disabled = false;
        document.getElementById('tv-stop-draw').classList.add('hidden');
    }
    
    updateUIForInactiveDraw() {
        document.getElementById('tv-draw-winner').classList.add('hidden');
        document.getElementById('tv-stop-draw').classList.add('hidden');
        document.getElementById('number-display').classList.remove('hidden');
        document.getElementById('number-display').textContent = 'NO ACTIVE DRAW';
        document.getElementById('winner-display').classList.add('hidden');
    }
    
    updateWinnersList() {
        const winnersList = document.getElementById('winners-list');
        winnersList.innerHTML = '';
        
        this.currentWinners.forEach(winner => {
            const winnerItem = document.createElement('div');
            winnerItem.className = 'winner-item';
            winnerItem.innerHTML = `
                <span>${winner.phone_number}</span>
                <span class="winner-position">${winner.position}${this.getOrdinalSuffix(winner.position)}</span>
            `;
            winnersList.appendChild(winnerItem);
        });
    }
    
    updateProgressInfo() {
        const progressInfo = document.getElementById('progress-info');
        const remaining = this.totalWinners - this.winnersDrawn;
        
        if (this.totalWinners > 1) {
            progressInfo.textContent = `${this.winnersDrawn} of ${this.totalWinners} winners drawn (${remaining} remaining)`;
            progressInfo.classList.remove('hidden');
        } else {
            progressInfo.classList.add('hidden');
        }
    }
    
    updateDrawInfo() {
        if (this.currentDraw) {
            document.getElementById('tv-draw-name').textContent = this.currentDraw.name.toUpperCase();
            document.getElementById('tv-prize-amount').textContent = `MWK ${this.currentDraw.prize_amount.toLocaleString()}`;
            
            // Update participant count
            fetch(`/api/participants/count/${this.currentDraw.id}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('tv-participant-count').textContent = `${data.count} Participants`;
                });
        }
    }
    
    startStatusUpdates() {
        setInterval(() => {
            this.updateDrawStatus();
        }, 3000);
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
    
    createConfetti() {
        const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f1c40f', '#9b59b6'];
        const shapes = ['circle', 'square', 'rectangle', 'triangle', 'diamond'];
        const container = document.getElementById('confetti-container');
        
        // Clear any existing confetti
        container.innerHTML = '';
        
        for (let i = 0; i < 200; i++) {
            const confetti = document.createElement('div');
            const shape = shapes[Math.floor(Math.random() * shapes.length)];
            confetti.className = `confetti ${shape}`;
            
            confetti.style.left = Math.random() * 100 + 'vw';
            
            confetti.style.top = '-20px';
            
            // Random color
            const color = colors[Math.floor(Math.random() * colors.length)];
            if (shape !== 'triangle') {
                confetti.style.backgroundColor = color;
            } else {
                confetti.style.borderBottomColor = color;
            }
            
            // Random size variations
            if (shape === 'circle' || shape === 'square' || shape === 'diamond') {
                const size = 6 + Math.random() * 8;
                confetti.style.width = size + 'px';
                confetti.style.height = size + 'px';
            } else if (shape === 'rectangle') {
                const width = 4 + Math.random() * 6;
                const height = 8 + Math.random() * 8;
                confetti.style.width = width + 'px';
                confetti.style.height = height + 'px';
            }
            
            // Random animation delay for staggered effect
            confetti.style.animationDelay = (Math.random() * 2) + 's';
            
            container.appendChild(confetti);
            
            // Remove confetti after animation completes
            setTimeout(() => {
                if (confetti.parentElement === container) {
                    confetti.remove();
                }
            }, 5000);
        }
    }
    
    showNotification(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// Initialize the raffle draw system when page loads
document.addEventListener('DOMContentLoaded', () => {
    new RaffleDrawTV();
});