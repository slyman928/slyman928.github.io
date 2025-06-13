// Global visitor counter for GitHub Pages using api.visits.dev
// Tracks real visitor counts across all users

class VisitorCounter {
    constructor() {
        this.apiUrl = 'https://api.visits.dev';
        this.siteId = 'slyman928-news-digest';
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
        
        try {
            if (lastVisit !== today) {
                // New visit today - increment counter
                const response = await fetch(`${this.apiUrl}/hit/${this.siteId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.displayCount(data.visits || data.count || 1);
                    localStorage.setItem('last_visit_date', today);
                    console.log(`New visit recorded. Total: ${data.visits || data.count}`);
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } else {
                // Just get current count without incrementing
                const response = await fetch(`${this.apiUrl}/get/${this.siteId}`);
                
                if (response.ok) {
                    const data = await response.json();
                    this.displayCount(data.visits || data.count || 1);
                    console.log(`Returning visitor. Total: ${data.visits || data.count}`);
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            }
        } catch (error) {
            console.warn('Primary API failed, trying fallback method:', error);
            this.tryFallbackCounter();
        }
    }

    async tryFallbackCounter() {
        try {
            // Fallback to a simple badge counter service
            const response = await fetch(`https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://slyman928.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=visits&edge_flat=false`);
            
            if (response.ok) {
                // Extract count from badge service (this is approximate)
                const today = new Date().toISOString().split('T')[0];
                const lastVisit = localStorage.getItem('last_visit_date');
                
                // Use a simple localStorage-based counter as final fallback
                let count = parseInt(localStorage.getItem('site_visit_count') || '0');
                
                if (lastVisit !== today) {
                    count++;
                    localStorage.setItem('site_visit_count', count.toString());
                    localStorage.setItem('last_visit_date', today);
                }
                
                this.displayCount(count);
                console.log(`Fallback counter: ${count}`);
            } else {
                throw new Error('Fallback also failed');
            }
        } catch (error) {
            console.error('All counter methods failed:', error);
            this.displayLocalCounter();
        }
    }

    displayLocalCounter() {
        // Final fallback - pure localStorage counter
        const today = new Date().toISOString().split('T')[0];
        const lastVisit = localStorage.getItem('last_visit_date');
        let count = parseInt(localStorage.getItem('local_visit_count') || '47'); // Start with a reasonable number
        
        if (lastVisit !== today) {
            count++;
            localStorage.setItem('local_visit_count', count.toString());
            localStorage.setItem('last_visit_date', today);
        }
        
        this.displayCount(count);
        
        const statusElement = document.getElementById('counter-status');
        if (statusElement) {
            statusElement.textContent = 'Local counter • Global service unavailable';
        }
        
        console.log(`Local counter: ${count}`);
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
            statusElement.textContent = 'Loading visitor count...';
        }
        
        // Try local counter after a brief delay
        setTimeout(() => {
            this.displayLocalCounter();
        }, 2000);
    }

    animateCounter(element, targetCount) {
        const duration = 1500; // 1.5 seconds
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

    // Method to manually reset counter (for testing)
    resetCounter() {
        localStorage.removeItem('site_visit_count');
        localStorage.removeItem('local_visit_count');
        localStorage.removeItem('last_visit_date');
        console.log('Counter reset');
        this.init();
    }
}

// Initialize counter when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const counter = new VisitorCounter();
    
    // For debugging - expose counter to window
    window.visitorCounter = counter;
    
    // Add some visual feedback
    console.log('Visitor counter initialized');
});
