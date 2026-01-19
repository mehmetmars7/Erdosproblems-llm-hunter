/**
 * Problem Hunting with LLMs - Main Application JavaScript
 */

// Utility functions

/**
 * Get URL parameters
 */
function getUrlParams() {
    return new URLSearchParams(window.location.search);
}

/**
 * Update URL without page reload
 */
function updateUrl(params) {
    const url = new URL(window.location);
    for (const [key, value] of Object.entries(params)) {
        if (value === null || value === undefined || value === '') {
            url.searchParams.delete(key);
        } else {
            url.searchParams.set(key, value);
        }
    }
    window.history.replaceState({}, '', url);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format TeX content for display
 * Preserves LaTeX while making it HTML-safe
 */
function formatTeXContent(text) {
    if (!text) return '';

    // First, escape HTML entities
    let formatted = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Convert double newlines to paragraph breaks
    formatted = formatted.split(/\n\n+/).map(para => {
        return '<p>' + para.replace(/\n/g, '<br>') + '</p>';
    }).join('');

    return formatted;
}

/**
 * Trigger MathJax to re-render
 */
function renderMath() {
    if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
        MathJax.typesetPromise().catch(function(err) {
            console.warn('MathJax typeset error:', err);
        });
    }
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Sort problems by number
 */
function sortByNumber(a, b) {
    const numA = parseInt(a.number || a.id) || 0;
    const numB = parseInt(b.number || b.id) || 0;
    return numA - numB;
}

/**
 * Sort problems by score (descending)
 */
function sortByScore(a, b) {
    return (b.score || 0) - (a.score || 0);
}

/**
 * Get unique models from attacks
 */
function getUniqueModels(attacks) {
    if (!attacks || !attacks.length) return [];
    return [...new Set(attacks.map(a => a.model))];
}

/**
 * Count problems with attacks
 */
function countWithAttacks(problems) {
    return Object.values(problems).filter(p => p.attacks && p.attacks.length > 0).length;
}

/**
 * Format date string
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch {
        return dateStr;
    }
}

/**
 * Get status class for styling
 */
function getStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'solved':
            return 'status-solved';
        case 'partial':
            return 'status-partial';
        case 'unresolved':
            return 'status-unresolved';
        default:
            return '';
    }
}

/**
 * Theme handling
 */
function getStoredTheme() {
    try {
        return localStorage.getItem('theme');
    } catch {
        return null;
    }
}

function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored === 'light' || stored === 'dark') return stored;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
    }
    return 'light';
}

function updateThemeToggle(theme) {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    toggle.textContent = theme === 'dark' ? 'Dark' : 'Light';
    toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    toggle.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
}

function updateGiscusTheme(theme) {
    const frame = document.querySelector('iframe.giscus-frame');
    if (!frame || !frame.contentWindow) return;
    frame.contentWindow.postMessage(
        { giscus: { setConfig: { theme: theme === 'dark' ? 'dark' : 'light' } } },
        'https://giscus.app'
    );
}

function applyTheme(theme, persist) {
    const nextTheme = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nextTheme);
    if (persist) {
        try {
            localStorage.setItem('theme', nextTheme);
        } catch {
            // Ignore storage errors
        }
    }
    updateThemeToggle(nextTheme);
    updateGiscusTheme(nextTheme);
}

function initThemeToggle() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    const initialTheme = getPreferredTheme();
    applyTheme(initialTheme, false);

    toggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next, true);
    });

    if (window.matchMedia) {
        const media = window.matchMedia('(prefers-color-scheme: dark)');
        if (media.addEventListener) {
            media.addEventListener('change', (event) => {
                if (getStoredTheme()) return;
                applyTheme(event.matches ? 'dark' : 'light', false);
            });
        }
    }
}

/**
 * Get review label for display
 */
function getReviewLabel(review) {
    const status = (review && review.status ? review.status : '').toLowerCase();
    switch (status) {
        case 'flagged':
        case 'incorrect':
        case 'technicality':
        case 'trivial':
        case 'partial':
        case 'plausible':
        case 'accepted':
            return status;
        default:
            return 'unreviewed';
    }
}

/**
 * Get review class for styling
 */
function getReviewClass(review) {
    if (!review || !review.status) return 'review-unreviewed';
    return `review-${review.status.toLowerCase()}`;
}

/**
 * Initialize collapsible sections
 */
function initCollapsibles() {
    document.querySelectorAll('.collapsible-header').forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('collapsible-content')) {
                content.classList.toggle('collapsed');
                header.classList.toggle('expanded');
            }
        });
    });
}

/**
 * Smooth scroll to element
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        return false;
    }
}

/**
 * Show a temporary message
 */
function showMessage(message, duration = 3000) {
    const existing = document.querySelector('.temp-message');
    if (existing) existing.remove();

    const div = document.createElement('div');
    div.className = 'temp-message';
    div.textContent = message;
    div.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 10px 20px;
        background: #333;
        color: white;
        border-radius: 4px;
        z-index: 1000;
    `;
    document.body.appendChild(div);

    setTimeout(() => div.remove(), duration);
}

// Export for use in other scripts
window.ProblemHunting = {
    getUrlParams,
    updateUrl,
    escapeHtml,
    formatTeXContent,
    renderMath,
    debounce,
    sortByNumber,
    sortByScore,
    getUniqueModels,
    countWithAttacks,
    formatDate,
    getStatusClass,
    getReviewLabel,
    getReviewClass,
    initThemeToggle,
    initCollapsibles,
    scrollToElement,
    copyToClipboard,
    showMessage
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();
    initCollapsibles();
});
