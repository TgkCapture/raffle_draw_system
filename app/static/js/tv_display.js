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
        this.isDrawComplete = false;
        
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
            
            if (data.is_running && !this.isDrawComplete) {
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
                
                // Show draw button if more winners to draw
                if (this.winnersDrawn < this.totalWinners) {
                    document.getElementById('tv-draw-winner').classList.remove('hidden');
                    document.getElementById('tv-draw-winner').disabled = false;
                } else {
                    document.getElementById('tv-draw-winner').classList.add('hidden');
                    document.getElementById('tv-stop-draw').classList.remove('hidden');
                }
            } else {
                this.isDrawing = false;
                this.updateUIForInactiveDraw();
            }
        } catch (error) {
            console.error('Error updating draw status:', error);
        }
    }
    
    async drawWinner() {
        if (!this.isDrawing || this.isDrawingInProgress) return;
        
        this.isDrawingInProgress = true;
        document.getElementById('tv-draw-winner').disabled = true;
        
        // Start animation for 10 seconds
        await this.startAnimation(10000);
    }
    
    async startAnimation(duration = 10000) {
        const numberDisplay = document.getElementById('number-display');
        const winnerDisplay = document.getElementById('winner-display');
        
        // Reset displays
        winnerDisplay.classList.add('hidden');
        numberDisplay.classList.remove('hidden');
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
                        // Proceed to draw the actual winner
                        this.drawActualWinner();
                        return;
                    }
                    
                    // Display the next phone number from the sequence
                    if (index < data.sequence.length) {
                        numberDisplay.textContent = this.maskPhoneNumber(data.sequence[index].phone_number);
                        index++;
                    } else {
                        index = 0;
                        numberDisplay.textContent = this.maskPhoneNumber(data.sequence[index].phone_number);
                        index++;
                    }
                }, 80); 
            } else {
                // Fallback if no sequence data
                this.fallbackAnimation(duration);
            }
        } catch (error) {
            console.error('Error getting animation:', error);
            // Fallback animation
            this.fallbackAnimation(duration);
        }
    }
    
    // Method to handle the actual winner drawing after animation
    async drawActualWinner() {
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
                
                // Check if draw is complete
                if (data.winner.draw_complete || this.winnersDrawn >= this.totalWinners) {
                    this.isDrawComplete = true;
                    document.getElementById('tv-stop-draw').classList.remove('hidden');
                    document.getElementById('tv-draw-winner').classList.add('hidden');
                } else {
                    // Re-enable draw button after 5 seconds to allow winner celebration
                    setTimeout(() => {
                        document.getElementById('tv-draw-winner').disabled = false;
                        this.isDrawingInProgress = false;
                    }, 5000);
                }
            } else {
                this.showNotification('Error drawing winner: ' + data.message, 'error');
                document.getElementById('tv-draw-winner').disabled = false;
                this.isDrawingInProgress = false;
            }
        } catch (error) {
            console.error('Error drawing winner:', error);
            this.showNotification('Error drawing winner', 'error');
            document.getElementById('tv-draw-winner').disabled = false;
            this.isDrawingInProgress = false;
        }
    }
    
    // Fallback animation if API fails
    fallbackAnimation(duration) {
        const numberDisplay = document.getElementById('number-display');
        const startTime = Date.now();
        let count = 0;
        
        this.animationInterval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            
            if (elapsed >= duration) {
                this.stopAnimation();
                this.drawActualWinner();
                return;
            }
 
            count++;
            numberDisplay.textContent = `Drawing ${count}...`;
            
        }, 80);
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
        winnerDisplay.textContent = this.maskPhoneNumber(winner.phone_number);
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
                this.isDrawComplete = true;
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
        
        // Reset winner display if needed
        const winnerDisplay = document.getElementById('winner-display');
        if (winnerDisplay.classList.contains('pulse')) {
            setTimeout(() => {
                winnerDisplay.classList.remove('pulse');
            }, 3000);
        }
    }
    
    updateUIForInactiveDraw() {
        document.getElementById('tv-draw-winner').classList.add('hidden');
        document.getElementById('tv-stop-draw').classList.add('hidden');
        document.getElementById('number-display').classList.remove('hidden');
        document.getElementById('number-display').textContent = 'DRAW COMPLETE';
        document.getElementById('winner-display').classList.add('hidden');
        
        // Reset state for next draw
        this.isDrawComplete = false;
        this.isDrawingInProgress = false;
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
            if (!this.isDrawingInProgress && !this.isDrawComplete) {
                this.updateDrawStatus();
            }
        }, 3000);
    }
    
    maskPhoneNumber(phoneNumber) {
        if (!phoneNumber || phoneNumber.length < 6) return phoneNumber;
        
        // Format: +265 XXX XXX XXX
        const prefix = phoneNumber.substring(0, 5);
        const suffix = phoneNumber.substring(phoneNumber.length - 3);
        
        return `${prefix} *** *** ${suffix}`;
    }
    
    createConfetti() {
        const colors = ['#941C26', '#000000', '#2ecc71', '#f1c40f', '#9b59b6'];
        const shapes = ['circle', 'square', 'rectangle', 'triangle', 'diamond'];
        const container = document.getElementById('confetti-container');
      
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
            
            confetti.style.animationDelay = (Math.random() * 2) + 's';
            
            container.appendChild(confetti);
            
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