// Theme switcher functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    const currentTheme = localStorage.getItem('theme');

    // Set initial theme
    if (currentTheme === 'dark' || (!currentTheme && prefersDarkScheme.matches)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        if (themeToggle) {
            themeToggle.checked = true;
            updateThemeIcon('moon');
        }
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        if (themeToggle) {
            updateThemeIcon('sun');
        }
    }

    // Toggle theme when switch is clicked
    if (themeToggle) {
        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                updateThemeIcon('moon');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                updateThemeIcon('sun');
            }
        });
    }

    // Update the theme icon based on the current theme
    function updateThemeIcon(iconType) {
        const themeIcon = document.getElementById('theme-icon');
        if (!themeIcon) return;
        
        if (iconType === 'sun') {
            themeIcon.className = 'fas fa-sun';
            themeIcon.title = 'Switch to Dark Mode';
        } else {
            themeIcon.className = 'fas fa-moon';
            themeIcon.title = 'Switch to Light Mode';
        }
    }
});
