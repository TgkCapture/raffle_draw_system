class RaffleDrawTV {
    constructor() {
        this.isDrawing = false;
        this.animationInterval = null;
        this.currentWinners = [];
        this.totalWinners = 0;
        this.winnersDrawn = 0;
        this.currentDraw = null;
        
        this.initializeEventListeners();
        this.updateDrawStatus();
        this.startStatusUpdates();
    }
    
    initializeEventListeners() {
        document.getElementById('tv-start-draw').addEventListener('click', () => this.startDraw());
        document.getElementById('tv-stop-draw').addEventListener('click', () => this.stopDraw());
        document.getElementById('tv-draw-winner').addEventListener('click', () => this.drawWinner());
        
        // Double click to exit TV mode (for admin)
        document.addEventListener('dblclick', () => {
            window.location.href = '/';
        });
    }
    
    async startDraw() {
        try {
            // Get current draw from server
            const drawsResponse = await fetch('/api/draws');
            const draws = await drawsResponse.json();
            const activeDraw = draws.find(d => d.status === 'active' || d.status === 'draft');
            
            if (!activeDraw) {
                this.showNotification('No available draws to start', 'error');
                return;
            }
            
            const response = await fetch(`/api/draws/${activeDraw.id}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isDrawing = true;
                this.currentDraw = activeDraw;
                this.totalWinners = activeDraw.number_of_winners;
                this.updateUIForDrawing();
                this.updateDrawInfo();
                this.showNotification('Draw started successfully!', 'success');
            } else {
                this.showNotification('Error: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('Error starting draw:', error);
            this.showNotification('Error starting draw', 'error');
        }
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
                this.stopAnimation();
                this.updateUIForStopped();
            }
        } catch (error) {
            console.error('Error stopping draw:', error);
        }
    }
    
    async drawWinner() {
        if (!this.isDrawing) return;
        
        // Start animation before drawing winner
        await this.startAnimation();
        
        try {
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
                
                // If draw is complete, stop the draw
                if (data.winner.draw_complete) {
                    setTimeout(() => {
                        this.stopDraw();
                        this.showFinalWinners();
                    }, 5000);
                } else {
                    // Continue to next winner after delay
                    setTimeout(() => {
                        this.resetForNextWinner();
                    }, 3000);
                }
            } else {
                alert('Error drawing winner: ' + data.message);
            }
        } catch (error) {
            console.error('Error drawing winner:', error);
        }
    }
    
    async startAnimation() {
        const numberDisplay = document.getElementById('number-display');
        numberDisplay.classList.add('spinning');
        numberDisplay.textContent = 'DRAWING...';
        
        // Get participant numbers for animation
        try {
            const response = await fetch(`/api/participants/${this.currentDraw.id}`);
            const participants = await response.json();
            
            if (participants.length > 0) {
                let index = 0;
                this.animationInterval = setInterval(() => {
                    if (index < participants.length) {
                        numberDisplay.textContent = participants[index].phone_number;
                        index++;
                    } else {
                        this.stopAnimation();
                    }
                }, 100);
            }
        } catch (error) {
            console.error('Error getting participants:', error);
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
    
    resetForNextWinner() {
        const numberDisplay = document.getElementById('number-display');
        const winnerDisplay = document.getElementById('winner-display');
        
        winnerDisplay.classList.remove('pulse');
        winnerDisplay.classList.add('hidden');
        numberDisplay.classList.remove('hidden');
        numberDisplay.textContent = 'READY FOR NEXT WINNER';
    }
    
    showFinalWinners() {
        const numberDisplay = document.getElementById('number-display');
        const winnerDisplay = document.getElementById('winner-display');
        const winnersList = document.getElementById('winners-list');
        
        numberDisplay.classList.add('hidden');
        winnerDisplay.classList.add('hidden');
        winnersList.classList.remove('hidden');
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
        if (this.totalWinners > 1) {
            progressInfo.textContent = `Winner ${this.winnersDrawn} of ${this.totalWinners}`;
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
    
    updateUIForDrawing() {
        document.getElementById('tv-start-draw').classList.add('hidden');
        document.getElementById('tv-stop-draw').classList.remove('hidden');
        document.getElementById('tv-draw-winner').classList.remove('hidden');
    }
    
    updateUIForStopped() {
        document.getElementById('tv-start-draw').classList.remove('hidden');
        document.getElementById('tv-stop-draw').classList.add('hidden');
        document.getElementById('tv-draw-winner').classList.add('hidden');
    }
    
    async updateDrawStatus() {
        try {
            const response = await fetch('/api/draws/status');
            const data = await response.json();
            
            if (data.is_running && !this.isDrawing) {
                this.isDrawing = true;
                this.totalWinners = data.total_winners;
                this.winnersDrawn = data.winners_drawn;
                this.updateUIForDrawing();
                this.updateProgressInfo();
                
                // Get current draw info
                const drawsResponse = await fetch('/api/draws');
                const draws = await drawsResponse.json();
                this.currentDraw = draws.find(d => d.id === data.current_draw);
                this.updateDrawInfo();
            }
        } catch (error) {
            console.error('Error updating draw status:', error);
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
        const container = document.body;
        
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.style.position = 'fixed';
            confetti.style.width = '10px';
            confetti.style.height = '10px';
            confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.borderRadius = '50%';
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.top = '-10px';
            confetti.style.zIndex = '9999';
            
            container.appendChild(confetti);
            
            const animation = confetti.animate([
                { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
                { transform: `translateY(100vh) rotate(${Math.random() * 360}deg)`, opacity: 0 }
            ], {
                duration: Math.random() * 3000 + 2000,
                easing: 'cubic-bezier(0.1, 0.8, 0.2, 1)'
            });
            
            animation.onfinish = () => confetti.remove();
        }
    }
}

// Initialize the raffle draw system when page loads
document.addEventListener('DOMContentLoaded', () => {
    new RaffleDrawTV();
});