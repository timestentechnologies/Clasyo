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
        
        // Get the html and body elements
        const html = document.documentElement;
        const body = document.body;
        
        // Remove all theme classes first
        html.classList.remove('theme-light', 'theme-dark');
        body.classList.remove('theme-light', 'theme-dark', 'dark-theme');
        html.removeAttribute('data-theme');
        
        // Apply the selected theme
        if (theme === 'dark') {
            // Set attributes on both html and body for maximum compatibility
            html.setAttribute('data-theme', 'dark');
            html.classList.add('theme-dark');
            body.classList.add('dark-theme');
            body.setAttribute('data-theme', 'dark');
            
            // Update the theme toggle if it exists
            if (themeToggle) themeToggle.checked = true;
            updateThemeIcon('moon');
            
            // Set the theme color meta tag for mobile browsers
            const themeColor = document.querySelector('meta[name="theme-color"]');
            if (themeColor) {
                themeColor.setAttribute('content', '#1A202C');
            }
        } else {
            // Light theme
            html.setAttribute('data-theme', 'light');
            html.classList.add('theme-light');
            body.removeAttribute('data-theme');
            
            // Update the theme toggle if it exists
            if (themeToggle) themeToggle.checked = false;
            updateThemeIcon('sun');
            
            // Reset the theme color meta tag for mobile browsers
            const themeColor = document.querySelector('meta[name="theme-color"]');
            if (themeColor) {
                themeColor.setAttribute('content', '#4f46e5');
            }
        }
        
        // Force a reflow to ensure styles are applied
        document.body.offsetHeight;
        
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

    // Check for saved theme preference or default to light
    let initialTheme = localStorage.getItem('theme') || 'light';
    
    // Apply the theme
    applyTheme(initialTheme);
    
    // Update the toggle state
    if (themeToggle) {
        themeToggle.checked = initialTheme === 'dark';
    }

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
