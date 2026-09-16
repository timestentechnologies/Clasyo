// Theme Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return; // Exit if no theme toggle found
    
    const themeIcon = themeToggle.querySelector('i');
    
    // Check for saved theme preference or use system preference
    const savedTheme = localStorage.getItem('theme') || 
                      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    
    // Apply theme to both html and body for maximum compatibility
    applyTheme(savedTheme);

    // Toggle theme on button click
    themeToggle.addEventListener('click', function(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        const currentTheme = document.documentElement.getAttribute('data-theme') || 
                             (document.documentElement.classList.contains('theme-dark') ? 'dark' : 'light');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });

    // Apply theme across html and body
    function applyTheme(theme) {
        const html = document.documentElement;
        const body = document.body;

        html.setAttribute('data-theme', theme);
        body.setAttribute('data-theme', theme);

        if (theme === 'dark') {
            html.classList.remove('theme-light', 'light-theme');
            body.classList.remove('theme-light', 'light-theme');
            html.classList.add('theme-dark', 'dark-theme');
            body.classList.add('theme-dark', 'dark-theme');
        } else {
            html.classList.remove('theme-dark', 'dark-theme');
            body.classList.remove('theme-dark', 'dark-theme');
            html.classList.add('theme-light', 'light-theme');
            body.classList.add('theme-light', 'light-theme');
        }

        updateThemeIcon(theme);
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: theme } }));
    }

    // Update the theme icon based on current theme
    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        const statusBadge = document.getElementById('themeStatusBadge');
        if (theme === 'light') {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
            themeToggle.setAttribute('title', 'Switch to Dark Mode');
            if (statusBadge) statusBadge.textContent = 'Light';
        } else {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
            themeToggle.setAttribute('title', 'Switch to Light Mode');
            if (statusBadge) statusBadge.textContent = 'Dark';
        }
    }
});

