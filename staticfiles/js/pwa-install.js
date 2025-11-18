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

// Create modal HTML
const modalHTML = `
<div id="pwa-install-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.7); z-index: 10000; display: flex; justify-content: center; align-items: center; animation: fadeIn 0.3s ease-out;">
    <div style="background: white; border-radius: 12px; width: 90%; max-width: 400px; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);">
        <div style="background: #00b4d8; padding: 24px; text-align: center; color: white;">
            <div style="font-size: 24px; font-weight: 600; margin-bottom: 10px;">Install Clasyo</div>
            <div style="opacity: 0.9; font-size: 15px;">Add to your home screen for quick access</div>
        </div>
        <div style="padding: 24px; text-align: center;">
            <div style="margin-bottom: 20px; color: #333; line-height: 1.5;">
                Enjoy a faster experience and quick access to your Clasyo learning platform.
            </div>
            <div style="display: flex; justify-content: center; gap: 12px; margin-top: 24px;">
                <button id="pwa-dismiss-btn" style="padding: 10px 20px; background: #f0f0f0; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; transition: all 0.2s ease;">
                    Not Now
                </button>
                <button id="pwa-install-btn" style="padding: 10px 24px; background: #00b4d8; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;">
                    <span>Install Now</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                </button>
            </div>
        </div>
        <div style="background: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #e9ecef;">
            Tap <span style="font-weight: 600;">Add to Home Screen</span> when prompted
        </div>
    </div>
</div>
<button id="pwa-floating-btn" style="position: fixed; bottom: 20px; right: 20px; width: 56px; height: 56px; border-radius: 50%; background: #00b4d8; color: white; border: none; cursor: pointer; z-index: 9999; box-shadow: 0 4px 14px rgba(0, 180, 216, 0.4); display: flex; justify-content: center; align-items: center; font-size: 24px; animation: pulse 2s infinite; transition: all 0.3s ease;">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>
</button>
`;

// Create modal container
const modalContainer = document.createElement('div');
modalContainer.innerHTML = modalHTML;
document.body.appendChild(modalContainer);

// Get modal elements
const pwaModal = document.getElementById('pwa-install-modal');
const pwaInstallBtn = document.getElementById('pwa-install-btn');
const pwaDismissBtn = document.getElementById('pwa-dismiss-btn');
const pwaFloatingBtn = document.getElementById('pwa-floating-btn');

// Add styles
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 4px 14px rgba(0, 180, 216, 0.4); }
        50% { transform: scale(1.05); box-shadow: 0 8px 20px rgba(0, 180, 216, 0.6); }
        100% { transform: scale(1); box-shadow: 0 4px 14px rgba(0, 180, 216, 0.4); }
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    #pwa-install-btn:hover, #pwa-floating-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 116, 217, 0.5);
    }
    #pwa-dismiss-btn:hover {
        background: #e0e0e0;
    }
`;
document.head.appendChild(style);

// Show/hide modal
const showModal = () => {
    pwaModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
};

const hideModal = () => {
    pwaModal.style.display = 'none';
    document.body.style.overflow = '';
};

let deferredPrompt;

// Function to check if the app is already installed
const isAppInstalled = () => {
    return window.matchMedia('(display-mode: standalone)').matches || 
           window.navigator.standalone || 
           document.referrer.includes('android-app://');
};

// Function to show the install prompt
const showInstallPrompt = () => {
    if (deferredPrompt && !isAppInstalled()) {
        // Show the floating button
        pwaFloatingBtn.style.display = 'flex';
        console.log('Floating button shown');
    }
};

// Listen for the beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
    console.log('beforeinstallprompt event received', e);
    e.preventDefault();
    deferredPrompt = e;
    
    // Show the floating button
    showInstallPrompt();
    
    // Handle floating button click
    pwaFloatingBtn.onclick = () => {
        showModal();
    };
    
    // Handle dismiss button click
    pwaDismissBtn.onclick = () => {
        hideModal();
    };
    
    // Handle install button click in modal
    pwaInstallBtn.onclick = () => {
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
                pwaFloatingBtn.style.display = 'none';
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