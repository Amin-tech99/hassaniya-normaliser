/**
 * JavaScript application for Hassaniya Arabic Normalizer web interface
 */

class HassaniyaNormalizer {
    constructor() {
        this.initializeElements();
        this.bindEvents();
        this.loadExample();
    }

    initializeElements() {
        // Input elements
        this.inputText = document.getElementById('inputText');
        this.normalizeBtn = document.getElementById('normalizeBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.exampleBtn = document.getElementById('exampleBtn');
        
        // Output elements
        this.outputText = document.getElementById('outputText');
        this.diffText = document.getElementById('diffText');
        
        // Stats elements
        this.totalWords = document.getElementById('totalWords');
        this.changedWords = document.getElementById('changedWords');
        this.changePercentage = document.getElementById('changePercentage');
        this.processingTime = document.getElementById('processingTime');
        
        // UI elements
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.errorToast = new bootstrap.Toast(document.getElementById('errorToast'));
        
        // Accordion sections
        this.outputSection = document.getElementById('outputSection');
        this.diffSection = document.getElementById('diffSection');
        this.statsSection = document.getElementById('statsSection');
    }

    bindEvents() {
        // Button events
        this.normalizeBtn.addEventListener('click', () => this.normalizeText());
        this.clearBtn.addEventListener('click', () => this.clearAll());
        this.exampleBtn.addEventListener('click', () => this.loadExample());
        
        // Keyboard shortcuts
        this.inputText.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.normalizeText();
            }
        });
        
        // Auto-resize textarea
        this.inputText.addEventListener('input', () => this.autoResizeTextarea());
    }

    autoResizeTextarea() {
        const textarea = this.inputText;
        textarea.style.height = 'auto';
        textarea.style.height = Math.max(150, textarea.scrollHeight) + 'px';
    }

    async normalizeText() {
        const text = this.inputText.value.trim();
        
        if (!text) {
            this.showError('Please enter some text to normalize.');
            return;
        }

        if (text.length > 10000) {
            this.showError('Text is too long. Maximum 10,000 characters allowed.');
            return;
        }

        try {
            this.setLoading(true);
            
            const response = await fetch('/api/normalize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            this.displayResults(data);
            this.expandAccordionSections();
            
        } catch (error) {
            console.error('Normalization error:', error);
            this.showError(`Failed to normalize text: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(data) {
        // Display normalized text
        this.outputText.innerHTML = this.escapeHtml(data.normalized);
        
        // Display diff with highlights
        this.diffText.innerHTML = data.diff;
        
        // Update statistics
        this.updateStats(data.stats);
        
        // Log success
        console.log('Normalization completed:', {
            originalLength: data.original.length,
            normalizedLength: data.normalized.length,
            stats: data.stats
        });
    }

    updateStats(stats) {
        this.totalWords.textContent = stats.total_words.toLocaleString();
        this.changedWords.textContent = stats.changed_words.toLocaleString();
        this.changePercentage.textContent = stats.change_percentage + '%';
        this.processingTime.textContent = stats.processing_time_ms;
        
        // Add visual feedback for changes
        if (stats.changed_words > 0) {
            this.changedWords.style.color = '#dc3545'; // Bootstrap danger color
        } else {
            this.changedWords.style.color = '#198754'; // Bootstrap success color
        }
    }

    expandAccordionSections() {
        // Expand output section
        if (!this.outputSection.classList.contains('show')) {
            const outputButton = document.querySelector('[data-bs-target="#outputSection"]');
            outputButton.click();
        }
        
        // Expand diff section if there are changes
        const changedWords = parseInt(this.changedWords.textContent.replace(/,/g, ''));
        if (changedWords > 0 && !this.diffSection.classList.contains('show')) {
            const diffButton = document.querySelector('[data-bs-target="#diffSection"]');
            diffButton.click();
        }
        
        // Expand stats section
        if (!this.statsSection.classList.contains('show')) {
            const statsButton = document.querySelector('[data-bs-target="#statsSection"]');
            statsButton.click();
        }
    }

    clearAll() {
        // Clear input
        this.inputText.value = '';
        this.autoResizeTextarea();
        
        // Clear output
        this.outputText.innerHTML = `
            <div class="text-muted text-center py-4">
                <i class="bi bi-arrow-up"></i>
                Normalized text will appear here
            </div>
        `;
        
        // Clear diff
        this.diffText.innerHTML = `
            <div class="text-muted text-center py-4">
                <i class="bi bi-arrow-up"></i>
                Changes will be highlighted here
            </div>
        `;
        
        // Reset stats
        this.totalWords.textContent = '-';
        this.changedWords.textContent = '-';
        this.changePercentage.textContent = '-';
        this.processingTime.textContent = '-';
        this.changedWords.style.color = '';
        
        // Focus input
        this.inputText.focus();
    }

    loadExample() {
        const exampleText = `هاذا النص مثال لتطبيك الحسانيه. 
فيه كلمات مثل "قال" و "ليه" و "شنه" اللي يحتاجو تطبيع.
النظام يقدر يعرف الكلمات المختلفه ويحولها للشكل الصحيح.`;
        
        this.inputText.value = exampleText;
        this.autoResizeTextarea();
        this.inputText.focus();
    }

    setLoading(isLoading) {
        if (isLoading) {
            this.normalizeBtn.disabled = true;
            this.normalizeBtn.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                Processing...
            `;
            this.loadingSpinner.style.display = 'block';
            this.loadingSpinner.classList.add('show');
        } else {
            this.normalizeBtn.disabled = false;
            this.normalizeBtn.innerHTML = `
                <i class="bi bi-arrow-right-circle"></i>
                Normalize Text
            `;
            this.loadingSpinner.classList.remove('show');
            setTimeout(() => {
                if (!this.loadingSpinner.classList.contains('show')) {
                    this.loadingSpinner.style.display = 'none';
                }
            }, 300);
        }
    }

    showError(message) {
        const errorMessage = document.getElementById('errorMessage');
        errorMessage.textContent = message;
        this.errorToast.show();
        
        // Log error for debugging
        console.error('Application error:', message);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Public API for external access
    async getStats() {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch stats:', error);
            return null;
        }
    }
}

// Utility functions
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        return new Promise((resolve, reject) => {
            if (document.execCommand('copy')) {
                resolve();
            } else {
                reject(new Error('Copy command failed'));
            }
            document.body.removeChild(textArea);
        });
    }
}

// Add copy functionality to output sections
function addCopyButtons() {
    const outputSection = document.querySelector('#outputSection .accordion-body');
    const diffSection = document.querySelector('#diffSection .accordion-body');
    
    if (outputSection && !outputSection.querySelector('.copy-btn')) {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-sm btn-outline-secondary copy-btn mt-2';
        copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
        copyBtn.addEventListener('click', async () => {
            const text = document.getElementById('outputText').textContent;
            try {
                await copyToClipboard(text);
                copyBtn.innerHTML = '<i class="bi bi-check"></i> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
                }, 2000);
            } catch (error) {
                console.error('Copy failed:', error);
            }
        });
        outputSection.appendChild(copyBtn);
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize main application
    window.normalizer = new HassaniyaNormalizer();
    
    // Add copy buttons
    addCopyButtons();
    
    // Add keyboard shortcuts info
    const inputText = document.getElementById('inputText');
    inputText.title = 'Tip: Press Ctrl+Enter to normalize text quickly';
    
    // Performance monitoring
    if ('performance' in window) {
        window.addEventListener('load', () => {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            console.log(`Page loaded in ${loadTime}ms`);
        });
    }
    
    // Service worker registration (if available)
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(err => {
            console.log('Service worker registration failed:', err);
        });
    }
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    if (window.normalizer) {
        window.normalizer.showError('An unexpected error occurred. Please refresh the page.');
    }
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    if (window.normalizer) {
        window.normalizer.showError('A network or processing error occurred.');
    }
});