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
        this.successToast = new bootstrap.Toast(document.getElementById('successToast'));
        
        // Accordion sections
        this.outputSection = document.getElementById('outputSection');
        this.diffSection = document.getElementById('diffSection');
        this.statsSection = document.getElementById('statsSection');
        
        // Variant form elements
        this.variantForm = document.getElementById('variantForm');
        this.canonicalInput = document.getElementById('canonicalInput');
        this.variantInput = document.getElementById('variantInput');
        this.addVariantBtn = document.getElementById('addVariantBtn');
        this.variantTableBody = document.getElementById('variantTableBody');
        
        // Link-fix form elements
        this.linkFixForm = document.getElementById('linkFixForm');
        this.wrongInput = document.getElementById('wrongInput');
        this.correctInput = document.getElementById('correctInput');
        this.addLinkFixBtn = document.getElementById('addLinkFixBtn');
        this.linkFixTableBody = document.getElementById('linkFixTableBody');
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
        
        // Variant form events
        if (this.variantForm) {
            this.variantForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addVariant();
            });
        }
        
        // Link-fix form events
        if (this.linkFixForm) {
            this.linkFixForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addLinkFix();
            });
        }
        
        // Tab change events to load data
        const variantTab = document.getElementById('variants-tab');
        // Corrected ID for Link-Fix tab button
        const linkFixTab = document.getElementById('linkfix-tab');
        
        if (variantTab) {
            variantTab.addEventListener('shown.bs.tab', () => this.loadRecentVariants());
        }
        
        if (linkFixTab) {
            linkFixTab.addEventListener('shown.bs.tab', () => this.loadRecentLinkFixes());
        }
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

        if (text.length > 100000) {
            this.showError('Text is too long. Maximum 100,000 characters allowed.');
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
    
    showSuccess(message) {
        const successMessage = document.getElementById('successMessage');
        successMessage.textContent = message;
        this.successToast.show();
    }
    
    async addVariant() {
        const canonical = this.canonicalInput.value.trim();
        const variantText = this.variantInput.value.trim();
        
        if (!canonical || !variantText) {
            this.showError('Both canonical and variant fields are required.');
            return;
        }
        
        // Split variants by lines and filter out empty lines
        const variants = variantText.split('\n')
            .map(v => v.trim())
            .filter(v => v.length > 0);
        
        if (variants.length === 0) {
            this.showError('Please enter at least one variant.');
            return;
        }
        
        try {
            this.addVariantBtn.disabled = true;
            this.addVariantBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';
            
            let successCount = 0;
            let errorCount = 0;
            
            // Add each variant separately
            for (const variant of variants) {
                try {
                    const response = await fetch('/api/variant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ canonical: canonical, variant: variant })
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        console.error(`Failed to add variant "${variant}":`, errorData.error);
                        errorCount++;
                    } else {
                        successCount++;
                        // Add to table
                        this.addVariantToTable(canonical, variant);
                    }
                } catch (error) {
                    console.error(`Error adding variant "${variant}":`, error);
                    errorCount++;
                }
            }
            
            // Show appropriate success/error message
            if (successCount > 0 && errorCount === 0) {
                this.showSuccess(`Successfully added ${successCount} variant(s)!`);
            } else if (successCount > 0 && errorCount > 0) {
                this.showSuccess(`Added ${successCount} variant(s). ${errorCount} failed.`);
            } else {
                this.showError(`Failed to add all ${errorCount} variant(s).`);
            }
            
            // Clear form if at least one variant was added successfully
            if (successCount > 0) {
                this.canonicalInput.value = '';
                this.variantInput.value = '';
            }
            
        } catch (error) {
            console.error('Add variant error:', error);
            this.showError(`Failed to add variants: ${error.message}`);
        } finally {
            this.addVariantBtn.disabled = false;
            this.addVariantBtn.innerHTML = 'Add Variants';
        }
    }
    
    async addLinkFix() {
        const wrong = this.wrongInput.value.trim();
        const correct = this.correctInput.value.trim();
        
        if (!wrong || !correct) {
            this.showError('Both incorrect and correct fields are required.');
            return;
        }
        
        try {
            // Re-query button in case reference was lost (e.g. Hot-reload, dynamic DOM changes)
            if (!this.addLinkFixBtn) {
                this.addLinkFixBtn = document.getElementById('addLinkFixBtn');
            }
            // Fallback: try to grab the submit button within the form
            if (!this.addLinkFixBtn && this.linkFixForm) {
                this.addLinkFixBtn = this.linkFixForm.querySelector('button[type="submit"]');
            }
            if (!this.addLinkFixBtn) {
                console.warn('Add Link-Fix button not found – proceeding without disabling the button');
            }
            this.addLinkFixBtn.disabled = true;
            this.addLinkFixBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';
            
            const response = await fetch('/api/link-fix', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ wrong: wrong, correct: correct })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.showSuccess('Link-fix added successfully!');
            
            // Clear form
            this.wrongInput.value = '';
            this.correctInput.value = '';
            
            // Add to table
            this.addLinkFixToTable(wrong, correct);
            
        } catch (error) {
            console.error('Add link-fix error:', error);
            this.showError(`Failed to add link-fix: ${error.message}`);
        } finally {
            if (!this.addLinkFixBtn) {
                this.addLinkFixBtn = document.getElementById('addLinkFixBtn');
            }
            if (this.addLinkFixBtn) {
                this.addLinkFixBtn.disabled = false;
            }
            if (this.addLinkFixBtn) {
                this.addLinkFixBtn.innerHTML = 'Add Link-Fix';
            }
        }
    }
    
    addVariantToTable(canonical, variant) {
        if (!this.variantTableBody) return;
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-end">${this.escapeHtml(canonical)}</td>
            <td class="text-end">${this.escapeHtml(variant)}</td>
        `;
        this.variantTableBody.insertBefore(row, this.variantTableBody.firstChild);
        
        // Keep only last 10 entries
        while (this.variantTableBody.children.length > 10) {
            this.variantTableBody.removeChild(this.variantTableBody.lastChild);
        }
    }
    
    addLinkFixToTable(wrong, correct) {
        if (!this.linkFixTableBody) return;
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-end">${this.escapeHtml(wrong)}</td>
            <td class="text-end">${this.escapeHtml(correct)}</td>
        `;
        this.linkFixTableBody.insertBefore(row, this.linkFixTableBody.firstChild);
        
        // Keep only last 10 entries
        while (this.linkFixTableBody.children.length > 10) {
            this.linkFixTableBody.removeChild(this.linkFixTableBody.lastChild);
        }
    }
    
    async loadRecentVariants() {
        if (!this.variantTableBody) return;
        
        try {
            const response = await fetch('/api/variant', {
                method: 'GET'
            });
            
            if (!response.ok) {
                console.error('Failed to load variants:', response.status);
                return;
            }
            
            const data = await response.json();
            
            // Clear existing table content
            this.variantTableBody.innerHTML = '';
            
            if (data.variants && data.variants.length > 0) {
                // Show variants in reverse order (most recent first)
                const recentVariants = data.variants.slice().reverse();
                
                recentVariants.forEach(entry => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="text-end">${this.escapeHtml(entry.canonical)}</td>
                        <td class="text-end">${this.escapeHtml(entry.variant)}</td>
                    `;
                    this.variantTableBody.appendChild(row);
                });
            } else {
                // Show empty state
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="2" class="text-muted text-center">No variants found</td>';
                this.variantTableBody.appendChild(row);
            }
            
        } catch (error) {
            console.error('Error loading variants:', error);
            // Show error state
            this.variantTableBody.innerHTML = '<tr><td colspan="2" class="text-muted text-center">Error loading variants</td></tr>';
        }
    }
    
    async loadRecentLinkFixes() {
        if (!this.linkFixTableBody) return;
        
        try {
            const response = await fetch('/api/link-fix', {
                method: 'GET'
            });
            
            if (!response.ok) {
                console.error('Failed to load link fixes:', response.status);
                return;
            }
            
            const data = await response.json();
            
            // Clear existing table content
            this.linkFixTableBody.innerHTML = '';
            
            if (data.link_fixes && data.link_fixes.length > 0) {
                // Show last 10 link fixes
                const recentLinkFixes = data.link_fixes.slice(-10).reverse();
                
                recentLinkFixes.forEach(entry => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="text-end">${this.escapeHtml(entry.wrong)}</td>
                        <td class="text-end">${this.escapeHtml(entry.correct)}</td>
                    `;
                    this.linkFixTableBody.appendChild(row);
                });
            } else {
                // Show empty state
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="2" class="text-muted text-center">No link fixes found</td>';
                this.linkFixTableBody.appendChild(row);
            }
            
        } catch (error) {
            console.error('Error loading link fixes:', error);
            // Show error state
            this.linkFixTableBody.innerHTML = '<tr><td colspan="2" class="text-muted text-center">Error loading link fixes</td></tr>';
        }
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