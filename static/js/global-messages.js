/**
 * Global System Message Modal System
 * Provides consistent popup modals for Success, Error, Warning, and Info messages across the entire application.
 */

(function() {
    /**
     * Display a styled modal message
     * @param {string} title - Title of the message
     * @param {string} message - Message content (supports HTML)
     * @param {boolean} isSuccess - True for success, false for error
     * @param {function} callback - Optional callback function when modal is closed
     * @param {string} type - 'success', 'error', 'danger', 'warning', 'info'
     */
    function showMessage(title, message, isSuccess = true, callback = null, type = null) {
        const modalEl = document.getElementById('messageModal');
        if (!modalEl) {
            console.warn('Message modal #messageModal not found in DOM');
            return;
        }
        
        const header = document.getElementById('messageModalHeader');
        const icon = document.getElementById('messageModalIcon');
        const titleText = document.getElementById('messageModalTitleText');
        const body = document.getElementById('messageModalBody');
        const btn = document.getElementById('messageModalBtn');
        
        // Resolve type
        let msgType = type;
        if (!msgType) {
            msgType = isSuccess ? 'success' : 'error';
        }
        msgType = msgType.toLowerCase();
        if (msgType === 'danger') msgType = 'error';
        
        // Set title
        if (titleText) {
            if (title) {
                titleText.textContent = title;
            } else {
                if (msgType === 'success') titleText.textContent = 'Success!';
                else if (msgType === 'error') titleText.textContent = 'Error';
                else if (msgType === 'warning') titleText.textContent = 'Warning';
                else titleText.textContent = 'Notice';
            }
        }
        
        // Set message content
        if (body) {
            body.innerHTML = message;
        }
        
        // Remove existing theme classes from header
        if (header) {
            header.classList.remove('msg-theme-success', 'msg-theme-error', 'msg-theme-danger', 'msg-theme-warning', 'msg-theme-info');
            header.classList.add('msg-theme-' + msgType);
        }
        
        // Set styling & iconography based on message type
        if (msgType === 'success') {
            if (header) header.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            if (icon) icon.className = 'fas fa-check-circle';
            if (btn) {
                btn.className = 'btn btn-success fw-semibold px-4 shadow-sm';
                btn.textContent = 'OK';
            }
        } else if (msgType === 'error') {
            if (header) header.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
            if (icon) icon.className = 'fas fa-exclamation-circle';
            if (btn) {
                btn.className = 'btn btn-danger fw-semibold px-4 shadow-sm';
                btn.textContent = 'Dismiss';
            }
        } else if (msgType === 'warning') {
            if (header) header.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
            if (icon) icon.className = 'fas fa-exclamation-triangle';
            if (btn) {
                btn.className = 'btn btn-warning fw-semibold px-4 shadow-sm text-dark';
                btn.textContent = 'Understood';
            }
        } else {
            // Info / default
            if (header) header.style.background = 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)';
            if (icon) icon.className = 'fas fa-info-circle';
            if (btn) {
                btn.className = 'btn btn-primary fw-semibold px-4 shadow-sm';
                btn.textContent = 'OK';
            }
        }
        
        // Handle callback when modal is closed
        if (callback && typeof callback === 'function') {
            modalEl.addEventListener('hidden.bs.modal', function onModalHidden() {
                callback();
                modalEl.removeEventListener('hidden.bs.modal', onModalHidden);
            }, { once: true });
        }
        
        // Show modal via Bootstrap
        if (window.bootstrap && window.bootstrap.Modal) {
            const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
            modalInstance.show();
        } else {
            $(modalEl).modal('show');
        }
    }

    /**
     * Show success popup modal
     */
    function showSuccess(message, callback = null, title = 'Success!') {
        showMessage(title, message, true, callback, 'success');
    }

    /**
     * Show error popup modal
     */
    function showError(message, callback = null, title = 'Error') {
        showMessage(title, message, false, callback, 'error');
    }

    /**
     * Show warning popup modal
     */
    function showWarning(message, callback = null, title = 'Warning') {
        showMessage(title, message, false, callback, 'warning');
    }

    /**
     * Show info popup modal
     */
    function showInfo(message, callback = null, title = 'Notice') {
        showMessage(title, message, true, callback, 'info');
    }

    /**
     * Show validation error message
     */
    function showValidationError(message) {
        showError(message, null, 'Validation Error');
    }

    /**
     * Show success message and reload page
     */
    function showSuccessAndReload(message, delay = 1500) {
        showSuccess(message, () => {
            setTimeout(() => location.reload(), delay);
        });
    }

    /**
     * Show success message and redirect
     */
    function showSuccessAndRedirect(message, url, delay = 1500) {
        showSuccess(message, () => {
            setTimeout(() => window.location.href = url, delay);
        });
    }

    /**
     * Show confirmation modal
     */
    function showConfirmation(title, message, onConfirm, onCancel) {
        const modalEl = document.getElementById('messageModal');
        if (!modalEl) return;

        const header = document.getElementById('messageModalHeader');
        const icon = document.getElementById('messageModalIcon');
        const titleText = document.getElementById('messageModalTitleText');
        const body = document.getElementById('messageModalBody');
        const btn = document.getElementById('messageModalBtn');

        if (header) {
            header.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
        }
        if (icon) {
            icon.className = 'fas fa-exclamation-triangle';
        }
        if (titleText) {
            titleText.textContent = title || 'Confirm Action';
        }
        if (body) {
            body.innerHTML = message;
        }

        // Setup confirm / cancel action
        let confirmed = false;
        if (btn) {
            btn.className = 'btn btn-warning fw-semibold px-4 shadow-sm text-dark';
            btn.textContent = 'Confirm';
            btn.onclick = function() {
                confirmed = true;
            };
        }

        modalEl.addEventListener('hidden.bs.modal', function onHidden() {
            modalEl.removeEventListener('hidden.bs.modal', onHidden);
            if (confirmed && onConfirm) {
                onConfirm();
            } else if (!confirmed && onCancel) {
                onCancel();
            }
        }, { once: true });

        const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
        modalInstance.show();
    }

    /**
     * Handle AJAX form submission with styled messages
     */
    function submitFormWithMessage(url, formData, successCallback = null, errorCallback = null) {
        fetch(url, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const message = data.message || 'Operation completed successfully!';
                showSuccess(message, () => {
                    if (successCallback) successCallback(data);
                });
            } else {
                const error = data.error || data.message || 'An error occurred';
                showError(error, () => {
                    if (errorCallback) errorCallback(data);
                });
            }
        })
        .catch(error => {
            showError('An unexpected error occurred: ' + error.message, () => {
                if (errorCallback) errorCallback(error);
            });
        });
    }

    /**
     * Auto-detect and display Django server-side messages as popup modals on page load
     */
    function initDjangoMessageModals() {
        var djangoContainer = document.getElementById('django-messages-container');
        if (!djangoContainer) return;

        var items = djangoContainer.querySelectorAll('.django-sys-message');
        if (!items || items.length === 0) return;

        var combinedMessages = [];
        var highestSeverity = 'info';

        items.forEach(function(item) {
            var tags = (item.getAttribute('data-tags') || '').toLowerCase();
            var text = item.innerHTML.trim();
            if (text) {
                combinedMessages.push(text);
            }

            if (tags.includes('error') || tags.includes('danger')) {
                highestSeverity = 'error';
            } else if (tags.includes('warning') && highestSeverity !== 'error') {
                highestSeverity = 'warning';
            } else if (tags.includes('success') && highestSeverity !== 'error' && highestSeverity !== 'warning') {
                highestSeverity = 'success';
            }
        });

        // Clear items immediately to prevent any re-triggering
        djangoContainer.innerHTML = '';

        if (combinedMessages.length > 0) {
            var fullMessage = combinedMessages.join('<br><br>');
            var title = 'Notice';
            if (highestSeverity === 'success') title = 'Success!';
            else if (highestSeverity === 'error') title = 'Error';
            else if (highestSeverity === 'warning') title = 'Warning';

            setTimeout(function() {
                showMessage(title, fullMessage, highestSeverity === 'success', null, highestSeverity);
            }, 120);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDjangoMessageModals);
    } else {
        initDjangoMessageModals();
    }

    // Expose functions globally
    window.showMessage = showMessage;
    window.showSuccess = showSuccess;
    window.showError = showError;
    window.showWarning = showWarning;
    window.showInfo = showInfo;
    window.showValidationError = showValidationError;
    window.showSuccessAndReload = showSuccessAndReload;
    window.showSuccessAndRedirect = showSuccessAndRedirect;
    window.showConfirmation = showConfirmation;
    window.submitFormWithMessage = submitFormWithMessage;
})();
