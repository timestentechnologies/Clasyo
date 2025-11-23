// pwa-install.js
// Prevent multiple script loads
if (window.pwaInstallInitialized) {
    console.log('PWA Install script already loaded, skipping re-initialization');
    throw new Error('PWA Install script already loaded');
}
window.pwaInstallInitialized = true;

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

// Create modal container if it doesn't exist
let modalContainer = document.getElementById('pwa-install-container');
let pwaModal, pwaInstallBtn, pwaDismissBtn, pwaFloatingBtn;

if (!modalContainer) {
    modalContainer = document.createElement('div');
    modalContainer.id = 'pwa-install-container';
    modalContainer.innerHTML = modalHTML;
    document.body.appendChild(modalContainer);
    
    // Get modal elements
    pwaModal = document.getElementById('pwa-install-modal');
    pwaInstallBtn = document.getElementById('pwa-install-btn');
    pwaDismissBtn = document.getElementById('pwa-dismiss-btn');
    pwaFloatingBtn = document.getElementById('pwa-floating-btn');
    
    // Store references in window object for future access
    window.pwaElements = {
        modal: pwaModal,
        installBtn: pwaInstallBtn,
        dismissBtn: pwaDismissBtn,
        floatingBtn: pwaFloatingBtn
    };
} else {
    // Use existing elements
    const elements = window.pwaElements || {};
    pwaModal = elements.modal;
    pwaInstallBtn = elements.installBtn;
    pwaDismissBtn = elements.dismissBtn;
    pwaFloatingBtn = elements.floatingBtn;
}

// Add styles only if they don't exist
if (!document.getElementById('pwa-install-styles')) {
    const style = document.createElement('style');
    style.id = 'pwa-install-styles';
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
}

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
    // Check various indicators that the app is installed
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    const isInWebApp = window.navigator.standalone === true;
    const isAndroidApp = document.referrer.includes('android-app://');
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const isManuallyMarkedInstalled = localStorage.getItem('pwaInstalled') === 'true';
    
    // For iOS, check if in standalone mode or if the app was previously marked as installed
    if (isIOS) {
        if (window.navigator.standalone || isManuallyMarkedInstalled) {
            pwaFloatingBtn.style.display = 'none';
            return true;
        }
        return false;
    }
    
    // For other platforms
    const isInstalled = isStandalone || isInWebApp || isAndroidApp || isManuallyMarkedInstalled;
    
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
    
    // Check if dismissed in local storage and when
    const dismissedAt = localStorage.getItem('pwaDismissedAt');
    const dismissalExpired = dismissedAt ? 
        (Date.now() - parseInt(dismissedAt, 10)) > (30 * 24 * 60 * 60 * 1000) : // 30 days
        true;
    
    // If dismissed in session or locally within the last 30 days
    if (sessionDismissed || (!dismissalExpired && localStorage.getItem('pwaDismissed') === 'true')) {
        console.log('Install prompt was previously dismissed');
        return true;
    }
    
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
        
        if (!deferredPrompt) {
            console.log('No deferred prompt available');
            return;
        }
        
        try {
            // Show the install prompt
            deferredPrompt.prompt();
            
            // Wait for the user to respond to the prompt
            const { outcome } = await deferredPrompt.userChoice;
            
            console.log(`User response to the install prompt: ${outcome}`);
            
            // Mark as installed if user accepted
            if (outcome === 'accepted') {
                localStorage.setItem('pwaInstalled', 'true');
                localStorage.setItem('pwaInstalledAt', Date.now().toString());
                console.log('User accepted the install prompt');
                
                // Also set as dismissed to prevent further prompts
                sessionStorage.setItem('pwaDismissed', 'true');
                localStorage.setItem('pwaDismissed', 'true');
                localStorage.setItem('pwaDismissedAt', Date.now().toString());
            }
            
            // Hide the install button and modal
            pwaFloatingBtn.style.display = 'none';
            hideModal();
            
        } catch (err) {
            console.error('Error showing install prompt:', err);
        }
        
        // Clear the deferredPrompt variable
        deferredPrompt = null;
    });
}

// Initialize event listeners
setupEventListeners();

// Listen for the beforeinstallprompt event
const handleBeforeInstallPrompt = (e) => {
    console.log('beforeinstallprompt event received', e);
    
    // Prevent the default browser install prompt
    e.preventDefault();
    
    // Store the event for later use
    window.deferredPrompt = e;
    
    // Check if we should show the prompt
    if (isAppInstalled() || isPromptDismissed()) {
        console.log('Not showing install prompt - app is installed or prompt was dismissed');
        return;
    }
    
    // Show the install prompt after a short delay
    setTimeout(() => {
        if (isPromptDismissed() || isAppInstalled()) {
            console.log('Not showing prompt - already dismissed or installed');
            return;
        }
        
        console.log('All conditions met, showing install prompt');
        showInstallPrompt();
    }, 3000); // 3 second delay
};

// Remove any existing event listeners to prevent duplicates
window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

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