// Theme switcher functionality
function initializeTheme() {
    const themeToggle = document.getElementById('theme-toggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    const currentTheme = localStorage.getItem('theme') || 'light';
    const html = document.documentElement;
    const body = document.body;
    const sidebar = document.querySelector('.modern-sidebar');

    // Function to apply theme
    function applyTheme(theme) {
        console.log('Applying theme:', theme);
        
        // Get the html element
        const html = document.documentElement;
        const body = document.body;
        
        // Remove all theme classes first
        html.classList.remove('theme-light', 'theme-dark');
        body.classList.remove('theme-light', 'theme-dark', 'dark-theme');
        html.removeAttribute('data-theme');
        
        // Apply the selected theme
        if (theme === 'dark') {
            html.setAttribute('data-theme', 'dark');
            html.classList.add('theme-dark');
            body.classList.add('dark-theme');
            if (themeToggle) themeToggle.checked = true;
            updateThemeIcon('moon');
            
            // Directly set sidebar styles for dark theme
            if (sidebar) {
                sidebar.style.background = 'linear-gradient(180deg, #1a202c 0%, #2d3748 100%)';
                sidebar.style.color = '#e2e8f0';
                
                // Update all links in sidebar
                const links = sidebar.querySelectorAll('a');
                links.forEach(link => {
                    link.style.color = '#e2e8f0';
                });
                
                // Update active state
                const activeItems = sidebar.querySelectorAll('.active');
                activeItems.forEach(item => {
                    item.style.background = 'rgba(66, 153, 225, 0.2)';
                    item.style.borderLeft = '3px solid #4299e1';
                });
            }
        } else {
            html.setAttribute('data-theme', 'light');
            html.classList.add('theme-light');
            if (themeToggle) themeToggle.checked = false;
            updateThemeIcon('sun');
            
            // Reset sidebar styles for light theme
            if (sidebar) {
                sidebar.style.background = 'linear-gradient(180deg, var(--primary-navy) 0%, var(--secondary-navy) 100%)';
                sidebar.style.color = '';
                
                // Reset all links in sidebar
                const links = sidebar.querySelectorAll('a');
                links.forEach(link => {
                    link.style.color = '';
                });
                
                // Reset active state
                const activeItems = sidebar.querySelectorAll('.active');
                activeItems.forEach(item => {
                    item.style.background = '';
                    item.style.borderLeft = '';
                });
            }
        }
        
        // Force a reflow/repaint to ensure styles are applied
        document.body.offsetHeight;
        
        // Debug: Log current theme classes
        console.log('Current theme classes:', {
            htmlDataTheme: html.getAttribute('data-theme'),
            bodyClasses: body.className,
            prefersDark: prefersDarkScheme.matches,
            localTheme: localStorage.getItem('theme'),
            sidebarStyles: sidebar ? window.getComputedStyle(sidebar) : 'No sidebar found'
        });
    }

    // Update the theme icon
    function updateThemeIcon(iconType) {
        const themeIcon = document.getElementById('theme-icon');
        if (!themeIcon) return;
        
        themeIcon.className = iconType === 'sun' ? 'fas fa-sun' : 'fas fa-moon';
        themeIcon.title = iconType === 'sun' ? 'Switch to Dark Mode' : 'Switch to Light Mode';
    }

    // Always default to light theme
    const initialTheme = 'light';
    applyTheme(initialTheme);
    localStorage.setItem('theme', 'light');

    // Toggle theme when switch is clicked
    if (themeToggle) {
        themeToggle.addEventListener('change', function() {
            const newTheme = this.checked ? 'dark' : 'light';
            localStorage.setItem('theme', newTheme);
            applyTheme(newTheme);
        });
    }

    // Listen for system theme changes (only if no explicit theme is set)
    prefersDarkScheme.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
}

// Initialize theme when DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTheme);
} else {
    initializeTheme();
}
