// pwa-install.js
console.log('PWA Install Script Loaded - Debug Version');

// Debug info
console.log('PWA Debug Info:', {
    isSecureContext: window.isSecureContext,
    isLocalhost: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
    protocol: window.location.protocol,
    serviceWorker: 'serviceWorker' in navigator,
    beforeInstallPrompt: 'BeforeInstallPromptEvent' in window
});

// Create a more visible install button
const installButton = document.createElement('button');
installButton.textContent = '📱 Install SchoolSaaS App';
installButton.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 24px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: white;
    border: none;
    border-radius: 50px;
    cursor: pointer;
    z-index: 9999;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
    font-weight: 600;
    font-size: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    animation: pulse 2s infinite;
    transition: all 0.3s ease;
`;

// Add pulse animation
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
`;
document.head.appendChild(style);

let deferredPrompt;

// Function to check if the app is already installed
const isAppInstalled = () => {
    return window.matchMedia('(display-mode: standalone)').matches || 
           window.navigator.standalone || 
           document.referrer.includes('android-app://');
};

// Function to show the install button
const showInstallPrompt = () => {
    if (deferredPrompt && !isAppInstalled()) {
        // Show the button
        document.body.appendChild(installButton);
        console.log('Install button shown');
    }
};

// Listen for the beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
    console.log('beforeinstallprompt event received', e);
    e.preventDefault();
    deferredPrompt = e;
    
    // Show the install button
    showInstallPrompt();
    
    // Handle button click
    installButton.onclick = () => {
        if (deferredPrompt) {
            console.log('Showing install prompt');
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('User accepted the install prompt');
                } else {
                    console.log('User dismissed the install prompt');
                }
                deferredPrompt = null;
                installButton.style.display = 'none';
            }).catch(error => {
                console.error('Error handling install prompt:', error);
            });
        }
    };
});

// Check if the app is already installed
if (isAppInstalled()) {
    console.log('App is already installed');
} else {
    console.log('App is not installed yet');
}

// Register service worker with correct scope
if ('serviceWorker' in navigator) {
    console.log('Attempting to register service worker...');
    window.addEventListener('load', () => {
        // Register the service worker from the static directory
        navigator.serviceWorker.register('/static/service-worker.js', { scope: '/static/' })
            .then(registration => {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
                return registration;
            })
            .catch(err => {
                console.error('ServiceWorker registration failed: ', err);
                // Fallback to root scope if needed
                console.log('Attempting registration with root scope...');
                return navigator.serviceWorker.register('/static/service-worker.js', { scope: '/' })
                    .then(registration => {
                        console.log('ServiceWorker registration successful with root scope: ', registration.scope);
                        return registration;
                    });
            })
            .then(registration => {
                if (registration) {
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                    // Send a message to the service worker to skip waiting
                    if (registration.waiting) {
                        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                    }
                }
            })
            .catch(err => {
                console.error('Fallback ServiceWorker registration failed: ', err);
            });
    });
}

// Show install button on page load if not already shown
window.addEventListener('load', () => {
    console.log('Page loaded, checking for deferredPrompt');
    if (deferredPrompt && !isAppInstalled()) {
        showInstallPrompt();
    }
});

// Debugging: Log service worker registration status
console.log('Service Worker supported:', 'serviceWorker' in navigator);
console.log('BeforeInstallPrompt supported:', 'BeforeInstallPromptEvent' in window);