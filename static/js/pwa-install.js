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
    if (isPromptDismissed() || isAppInstalled()) {
        console.log('Not showing modal - prompt was dismissed or app is installed');
        pwaModal.style.display = 'none';
        pwaFloatingBtn.style.display = 'none';
        return;
    }
    
    console.log('Showing PWA install modal');
    pwaModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    // Track that we've shown the modal in this session
    promptShownInSession = true;
};

const hideModal = () => {
    pwaModal.style.display = 'none';
    document.body.style.overflow = '';
};

let deferredPrompt;

// Track if prompt was shown in this session
let promptShownInSession = false;

// Function to check if the app is already installed
const isAppInstalled = () => {
    const isInstalled = window.matchMedia('(display-mode: standalone)').matches || 
                       window.navigator.standalone || 
                       document.referrer.includes('android-app://') ||
                       localStorage.getItem('pwaInstalled') === 'true';
    
    if (isInstalled) {
        // Hide the floating button if app is installed
        pwaFloatingBtn.style.display = 'none';
        return true;
    }
    return false;
};

// Function to check if prompt was recently dismissed
const isPromptDismissed = () => {
    // Check if dismissed in this session
    const sessionDismissed = sessionStorage.getItem('pwaDismissed') === 'true';
    const localDismissed = localStorage.getItem('pwaDismissed') === 'true';
    
    console.log('Prompt dismissal status:', {
        sessionDismissed,
        localDismissed,
        sessionStorage: sessionStorage.getItem('pwaDismissed'),
        localStorage: localStorage.getItem('pwaDismissed')
    });
    
    if (sessionDismissed || localDismissed) {
        console.log('Prompt was dismissed');
        return true;
    }
    
    console.log('Prompt was not dismissed');
    return false;
};

// Function to show the install prompt
const showInstallPrompt = () => {
    if (isPromptDismissed()) {
        console.log('Not showing prompt - already dismissed');
        pwaFloatingBtn.style.display = 'none';
        return;
    }
    
    if (isAppInstalled()) {
        console.log('Not showing prompt - app is installed');
        pwaFloatingBtn.style.display = 'none';
        return;
    }
    
    if (!deferredPrompt) {
        console.log('No deferred prompt available');
        pwaFloatingBtn.style.display = 'none';
        return;
    }
    
    console.log('Showing floating button');
    pwaFloatingBtn.style.display = 'flex';
};

// Set up event listeners once when the script loads
function setupEventListeners() {
    // Handle floating button click
    pwaFloatingBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        showModal();
    });
    
    // Handle dismiss button click
    pwaDismissBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        hideModal();
        
        // Mark as dismissed in both session and local storage
        const timestamp = Date.now();
        sessionStorage.setItem('pwaDismissed', 'true');
        localStorage.setItem('pwaDismissed', 'true');
        localStorage.setItem('pwaDismissedAt', timestamp.toString());
        
        console.log('Install prompt dismissed at', new Date(timestamp).toISOString());
        
        // Hide the floating button
        pwaFloatingBtn.style.display = 'none';
        
        // Clear the deferred prompt
        if (deferredPrompt) {
            console.log('Clearing deferred prompt');
            deferredPrompt = null;
        }
    });
    
    // Close modal when clicking outside the modal content
    pwaModal.addEventListener('click', (e) => {
        if (e.target === pwaModal) {
            hideModal();
        }
    });
    
    // Handle install button click in modal
    pwaInstallBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (deferredPrompt) {
            try {
                console.log('Showing install prompt');
                // Show the browser's install prompt
                const { outcome } = await deferredPrompt.prompt();
                
                if (outcome === 'accepted') {
                    console.log('User accepted the install prompt');
                    localStorage.setItem('pwaInstalled', 'true');
                } else {
                    console.log('User dismissed the install prompt');
                    // Mark as dismissed in both session and local storage
                    sessionStorage.setItem('pwaDismissed', 'true');
                    localStorage.setItem('pwaDismissed', 'true');
                }
            } catch (error) {
                console.error('Error showing install prompt:', error);
            } finally {
                hideModal();
                pwaFloatingBtn.style.display = 'none';
                deferredPrompt = null;
            }
        }
    });
}

// Initialize event listeners
setupEventListeners();

// Listen for the beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
    console.group('=== beforeinstallprompt Event ===');
    console.log('Event details:', e);
    
    // Store the event for later use
    deferredPrompt = e;
    
    // Always prevent the default prompt
    e.preventDefault();
    
    console.log('Checking prompt conditions:');
    
    // Debug storage state
    console.log('Storage state:', {
        sessionDismissed: sessionStorage.getItem('pwaDismissed'),
        localDismissed: localStorage.getItem('pwaDismissed'),
        dismissedAt: localStorage.getItem('pwaDismissedAt'),
        isInstalled: localStorage.getItem('pwaInstalled')
    });
    
    // Check if we should show our custom prompt
    if (isPromptDismissed()) {
        console.log('Not showing prompt - already dismissed');
        pwaFloatingBtn.style.display = 'none';
        console.groupEnd();
        return;
    }
    
    if (isAppInstalled()) {
        console.log('Not showing prompt - app is installed');
        pwaFloatingBtn.style.display = 'none';
        console.groupEnd();
        return;
    }
    
    console.log('All conditions met, showing install prompt');
    showInstallPrompt();
    console.groupEnd();
});

// Check if the app is already installed
if (isAppInstalled()) {
    console.log('App is already installed');
} else {
    console.log('App is not installed yet');
}

// Clean up any existing service workers
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => {
        return Promise.all(registrations.map(registration => registration.unregister()));
    }).then(() => {
        return caches.keys().then(cacheNames => {
            return Promise.all(cacheNames.map(cacheName => caches.delete(cacheName)));
        });
    }).catch(error => {
        console.warn('Error during service worker cleanup:', error);
    });
}

// Handle page load
window.addEventListener('load', () => {
    console.log('Page loaded, checking PWA install status');
    
    // Always hide the button and modal by default
    pwaFloatingBtn.style.display = 'none';
    pwaModal.style.display = 'none';
    
    // Check if prompt was dismissed or app is already installed
    if (isPromptDismissed() || isAppInstalled()) {
        console.log('Not showing prompt -', 
            isPromptDismissed() ? 'prompt was dismissed' : 'app is already installed');
        return;
    }
    
    // If we have a deferred prompt, show the install prompt after a short delay
    // This ensures the page is fully loaded before showing the prompt
    if (deferredPrompt) {
        console.log('All conditions met, will show install prompt');
        // Small delay to ensure the page is fully rendered
        setTimeout(() => {
            if (!isPromptDismissed() && !isAppInstalled()) {
                showInstallPrompt();
            }
        }, 1000);
    } else {
        console.log('No deferred prompt available, cannot show install prompt');
    }
});

// Debugging: Log PWA capabilities
console.log('PWA Capabilities:', {
    serviceWorker: 'serviceWorker' in navigator,
    beforeInstallPrompt: 'BeforeInstallPromptEvent' in window,
    isInstalled: isAppInstalled(),
    isDismissed: isPromptDismissed()
});