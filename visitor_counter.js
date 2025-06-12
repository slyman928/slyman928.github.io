// Global visitor counter for GitHub Pages using CountAPI
// Tracks real visitor counts across all users

class VisitorCounter {
    constructor() {
        this.apiUrl = 'https://api.countapi.xyz';
        this.namespace = 'slyman928-news-digest';
        this.key = 'page-visits';
        this.init();
    }

    async init() {
        try {
            await this.incrementAndDisplay();
        } catch (error) {
            console.error('Counter error:', error);
            this.displayFallback();
        }
    }

    async incrementAndDisplay() {
        // Check if user already visited today to avoid spam
        const today = new Date().toISOString().split('T')[0];
        const lastVisit = localStorage.getItem('last_visit_date');
        
        if (lastVisit !== today) {
            // New visit today - increment counter
            const response = await fetch(`${this.apiUrl}/hit/${this.namespace}/${this.key}`);
            const data = await response.json();
            
            if (data.value) {
                this.displayCount(data.value);
                localStorage.setItem('last_visit_date', today);
                console.log(`New visit recorded. Total: ${data.value}`);
            } else {
                throw new Error('Failed to increment counter');
            }
        } else {
            // Just get current count without incrementing
            const response = await fetch(`${this.apiUrl}/get/${this.namespace}/${this.key}`);
            const data = await response.json();
            
            if (data.value) {
                this.displayCount(data.value);
                console.log(`Returning visitor. Total: ${data.value}`);
            } else {
                throw new Error('Failed to get counter');
            }
        }
    }

    displayCount(count) {
        const counterElement = document.getElementById('visitor-counter');
        if (counterElement) {
            this.animateCounter(counterElement, count);
        }
        
        // Update status text
        const statusElement = document.getElementById('counter-status');
        if (statusElement) {
            const today = new Date().toISOString().split('T')[0];
            const lastVisit = localStorage.getItem('last_visit_date');
            const isNewVisit = lastVisit !== today;
            
            statusElement.textContent = isNewVisit ? 
                'Global counter • Thank you for visiting!' : 
                'Global counter • Welcome back today!';
        }
    }

    displayFallback() {
        const counterElement = document.getElementById('visitor-counter');
        if (counterElement) {
            counterElement.textContent = 'Loading...';
        }
        
        const statusElement = document.getElementById('counter-status');
        if (statusElement) {
            statusElement.textContent = 'Counter temporarily unavailable';
        }
    }

    animateCounter(element, targetCount) {
        const duration = 1500; // 1.5 seconds
        const startCount = Math.max(0, targetCount - 50);
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

    // Method to reset counter (for testing - remove in production)
    async resetCounter() {
        try {
            const response = await fetch(`${this.apiUrl}/set/${this.namespace}/${this.key}?value=0`);
            const data = await response.json();
            console.log('Counter reset:', data);
            return data;
        } catch (error) {
            console.error('Reset failed:', error);
        }
    }
}

// Initialize counter when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const counter = new VisitorCounter();
    
    // For debugging - expose counter to window (remove in production)
    window.visitorCounter = counter;
});
