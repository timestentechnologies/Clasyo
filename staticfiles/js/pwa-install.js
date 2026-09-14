// pwa-install.js
(function () {
    if (window.pwaInstallInitialized) {
        return;
    }
    window.pwaInstallInitialized = true;

    const SNOOZE_PERIOD_MS = 5 * 24 * 60 * 60 * 1000; // 5 days in milliseconds

    // 1. Immediately inject critical CSS into <head> to prevent ANY flash on load
    if (!document.getElementById('pwa-install-styles')) {
        const style = document.createElement('style');
        style.id = 'pwa-install-styles';
        style.textContent = `
            #pwa-install-container, #pwa-install-modal, #pwa-floating-btn {
                display: none !important;
            }
            #pwa-install-modal.pwa-active {
                display: flex !important;
            }
            #pwa-floating-btn.pwa-active {
                display: flex !important;
            }
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
            #pwa-dismiss-btn:hover { background: #e2e8f0; }
            #pwa-never-btn:hover { background: #f8fafc; color: #64748b; }
            #pwa-close-x:hover { background: rgba(255,255,255,0.4); }
        `;
        document.head.appendChild(style);
    }

    const isAppInstalled = () => {
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        const isInWebApp = window.navigator.standalone === true;
        const isAndroidApp = document.referrer.includes('android-app://');
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        const isManuallyMarkedInstalled = localStorage.getItem('pwaInstalled') === 'true';

        if (isIOS) {
            return window.navigator.standalone || isManuallyMarkedInstalled;
        }
        return isStandalone || isInWebApp || isAndroidApp || isManuallyMarkedInstalled;
    };

    const isPromptDismissed = () => {
        // 1. Permanent suppression ("Never Ask Again")
        if (localStorage.getItem('pwaNeverShow') === 'true') {
            return true;
        }

        // 2. 5-day snooze window
        const dismissedAt = localStorage.getItem('pwaDismissedAt');
        if (dismissedAt) {
            const timePassed = Date.now() - parseInt(dismissedAt, 10);
            if (timePassed < SNOOZE_PERIOD_MS) {
                return true; // Still within 5-day snooze
            }
        }

        return false;
    };

    const modalHTML = `
    <div id="pwa-install-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.7); z-index: 10000; justify-content: center; align-items: center; animation: fadeIn 0.3s ease-out;">
        <div style="background: white; border-radius: 12px; width: 90%; max-width: 420px; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); position: relative;">
            <button id="pwa-close-x" style="position: absolute; top: 12px; right: 12px; background: rgba(255,255,255,0.2); border: none; color: white; width: 28px; height: 28px; border-radius: 50%; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; z-index: 1;">&times;</button>
            <div style="background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%); padding: 24px; text-align: center; color: white;">
                <div style="font-size: 22px; font-weight: 700; margin-bottom: 6px;">Install Clasyo App</div>
                <div style="opacity: 0.9; font-size: 14px;">Add to your home screen for quick access</div>
            </div>
            <div style="padding: 24px; text-align: center;">
                <div style="margin-bottom: 20px; color: #495057; font-size: 14px; line-height: 1.5;">
                    Enjoy a faster experience and quick access to your Clasyo learning platform directly from your device.
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <button id="pwa-install-btn" style="padding: 12px 20px; background: #00b4d8; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s ease;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>Install Now</span>
                    </button>
                    <div style="display: flex; justify-content: space-between; gap: 8px; margin-top: 4px;">
                        <button id="pwa-dismiss-btn" style="flex: 1; padding: 10px 14px; background: #f1f5f9; color: #475569; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; transition: all 0.2s ease;">
                            Not Now (5 Days)
                        </button>
                        <button id="pwa-never-btn" style="flex: 1; padding: 10px 14px; background: transparent; color: #94a3b8; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; transition: all 0.2s ease;">
                            Never Ask Again
                        </button>
                    </div>
                </div>
            </div>
            <div style="background: #f8fafc; padding: 10px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0;">
                Tap <span style="font-weight: 600;">Add to Home Screen</span> when prompted
            </div>
        </div>
    </div>
    <button id="pwa-floating-btn" style="position: fixed; bottom: 20px; right: 20px; width: 56px; height: 56px; border-radius: 50%; background: #00b4d8; color: white; border: none; cursor: pointer; z-index: 9999; box-shadow: 0 4px 14px rgba(0, 180, 216, 0.4); justify-content: center; align-items: center; font-size: 24px; animation: pulse 2s infinite; transition: all 0.3s ease;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
    </button>
    `;

    const initPWA = () => {
        let modalContainer = document.getElementById('pwa-install-container');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'pwa-install-container';
            modalContainer.innerHTML = modalHTML;
            document.body.appendChild(modalContainer);
        }

        const pwaModal = document.getElementById('pwa-install-modal');
        const pwaInstallBtn = document.getElementById('pwa-install-btn');
        const pwaDismissBtn = document.getElementById('pwa-dismiss-btn');
        const pwaNeverBtn = document.getElementById('pwa-never-btn');
        const pwaCloseX = document.getElementById('pwa-close-x');
        const pwaFloatingBtn = document.getElementById('pwa-floating-btn');

        const hideModal = () => {
            if (pwaModal) pwaModal.classList.remove('pwa-active');
            document.body.style.overflow = '';
        };

        const showModal = () => {
            if (isPromptDismissed() || isAppInstalled()) {
                hideModal();
                if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
                return;
            }
            if (modalContainer) modalContainer.style.display = 'block';
            if (pwaModal) pwaModal.classList.add('pwa-active');
            document.body.style.overflow = 'hidden';
        };

        const snoozePrompt = () => {
            const timestamp = Date.now();
            localStorage.setItem('pwaDismissedAt', timestamp.toString());
            sessionStorage.setItem('pwaDismissed', 'true');
        };

        // If user already dismissed (5 days snooze or Never), hide everything immediately
        if (isPromptDismissed() || isAppInstalled()) {
            hideModal();
            if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
        }

        let deferredPrompt = null;

        // Snooze for 5 days on Not Now
        if (pwaDismissBtn) {
            pwaDismissBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                snoozePrompt();
                hideModal();
                if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
            });
        }

        // Snooze for 5 days on Close X
        if (pwaCloseX) {
            pwaCloseX.addEventListener('click', (e) => {
                e.stopPropagation();
                snoozePrompt();
                hideModal();
                if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
            });
        }

        // Suppress permanently on Never Ask Again
        if (pwaNeverBtn) {
            pwaNeverBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                hideModal();
                localStorage.setItem('pwaNeverShow', 'true');
                sessionStorage.setItem('pwaDismissed', 'true');
                if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
            });
        }

        // Backdrop click -> snooze 5 days
        if (pwaModal) {
            pwaModal.addEventListener('click', (e) => {
                if (e.target === pwaModal) {
                    snoozePrompt();
                    hideModal();
                    if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
                }
            });
        }

        // Escape key -> snooze 5 days
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && pwaModal && pwaModal.classList.contains('pwa-active')) {
                snoozePrompt();
                hideModal();
                if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
            }
        });

        if (pwaFloatingBtn) {
            pwaFloatingBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                showModal();
            });
        }

        if (pwaInstallBtn) {
            pwaInstallBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (!deferredPrompt) return;

                try {
                    deferredPrompt.prompt();
                    const { outcome } = await deferredPrompt.userChoice;
                    if (outcome === 'accepted') {
                        localStorage.setItem('pwaInstalled', 'true');
                        localStorage.setItem('pwaInstalledAt', Date.now().toString());
                        sessionStorage.setItem('pwaDismissed', 'true');
                    }
                    if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
                    hideModal();
                } catch (err) {
                    console.error('Error showing install prompt:', err);
                }
                deferredPrompt = null;
            });
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;

            if (isAppInstalled() || isPromptDismissed()) {
                if (pwaFloatingBtn) pwaFloatingBtn.classList.remove('pwa-active');
                hideModal();
                return;
            }

            // Show floating install button if eligible
            if (pwaFloatingBtn) pwaFloatingBtn.classList.add('pwa-active');
        });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPWA);
    } else {
        initPWA();
    }
})();