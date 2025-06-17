// Custom API-based visitor counter for GitHub Pages
// Connects to your cousin's Node.js server

class VisitorCounter {
    constructor() {
        // Change to HTTPS if your cousin's server supports it
        this.apiUrl = 'http://173.64.4.70:3001/api/visits';
        this.clientId = this.generateClientId();
        this.init();
    }

    generateClientId() {
        // Generate a semi-persistent client ID
        let clientId = localStorage.getItem('visit_client_id');
        if (!clientId) {
            clientId = 'client_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
            localStorage.setItem('visit_client_id', clientId);
        }
        return clientId;
    }

    async init() {
        try {
            await this.handleVisit();
        } catch (error) {
            console.error('Counter error:', error);
            this.showFallback();
        }
    }

    async handleVisit() {
        const today = new Date().toISOString().split('T')[0];
        const lastVisit = localStorage.getItem('last_api_visit_date');
        
        try {
            if (lastVisit !== today) {
                // New visit today - increment counter
                const response = await fetch(this.apiUrl + '/increment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        clientId: this.clientId
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.displayCount(data.totalVisits);
                    this.updateStatus('Global API counter • Thank you for visiting!');
                    localStorage.setItem('last_api_visit_date', today);
                    console.log(`New visit recorded: ${data.totalVisits}`);
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } else {
                // Just get current count
                const response = await fetch(this.apiUrl);
                
                if (response.ok) {
                    const data = await response.json();
                    this.displayCount(data.totalVisits);
                    this.updateStatus('Global API counter • Welcome back today!');
                    console.log(`Current visits: ${data.totalVisits}`);
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            }
        } catch (error) {
            console.warn('API counter failed, using fallback:', error);
            this.showFallback();
        }
    }

    displayCount(count) {
        const counterElement = document.getElementById('visitor-counter');
        if (counterElement) {
            this.animateCounter(counterElement, count);
        }
    }

    showFallback() {
        // Fallback to localStorage if API is unavailable
        const today = new Date().toISOString().split('T')[0];
        const lastVisit = localStorage.getItem('last_fallback_visit_date');
        
        let count = parseInt(localStorage.getItem('fallback_visit_count') || '234');
        
        if (lastVisit !== today) {
            count++;
            localStorage.setItem('fallback_visit_count', count.toString());
            localStorage.setItem('last_fallback_visit_date', today);
        }
        
        this.displayCount(count);
        this.updateStatus('Local counter • API temporarily unavailable');
        console.log(`Fallback counter: ${count}`);
    }

    animateCounter(element, targetCount) {
        if (!element) return;
        
        const duration = 1500;
        const startCount = Math.max(0, targetCount - 20);
        const increment = (targetCount - startCount) / (duration / 50);
        let currentCount = startCount;

        const timer = setInterval(() => {
            currentCount += increment;
            if (currentCount >= targetCount) {
                currentCount = targetCount;
                clearInterval(timer);
            }
            
            element.textContent = Math.floor(currentCount).toLocaleString();
        }, 50);
    }

    updateStatus(statusText) {
        const statusElement = document.getElementById('counter-status');
        if (statusElement) {
            statusElement.textContent = statusText;
        }
    }

    // Method to get stats (for debugging)
    async getStats() {
        try {
            const response = await fetch(this.apiUrl.replace('/visits', '/stats'));
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to get stats:', error);
        }
        return null;
    }

    // Debug method to reset counters
    resetAllCounters() {
        localStorage.removeItem('visit_client_id');
        localStorage.removeItem('last_api_visit_date');
        localStorage.removeItem('fallback_visit_count');
        localStorage.removeItem('last_fallback_visit_date');
        console.log('All counters reset');
        this.init();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const counter = new VisitorCounter();
    window.visitorCounter = counter;
    console.log('API-based visitor counter initialized');
});
