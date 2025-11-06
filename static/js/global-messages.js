/**
 * Global Message Modal System
 * Shows styled success/error messages across the application
 */

/**
 * Display a styled modal message
 * @param {string} title - Title of the message
 * @param {string} message - Message content (supports HTML)
 * @param {boolean} isSuccess - True for success (green), false for error (red)
 * @param {function} callback - Optional callback function when modal is closed
 */
function showMessage(title, message, isSuccess = true, callback = null) {
    const modal = document.getElementById('messageModal');
    if (!modal) {
        console.error('Message modal not found in DOM');
        return;
    }
    
    const modalInstance = new bootstrap.Modal(modal);
    const header = document.getElementById('messageModalHeader');
    const icon = document.getElementById('messageModalIcon');
    const titleText = document.getElementById('messageModalTitleText');
    const body = document.getElementById('messageModalBody');
    const btn = document.getElementById('messageModalBtn');
    
    // Set title
    if (titleText) {
        titleText.textContent = title;
    }
    
    // Set message
    if (body) {
        body.innerHTML = message;
    }
    
    // Set styling based on success/error
    if (isSuccess) {
        header.style.background = 'linear-gradient(180deg, #4CAF50 0%, #45a049 100%)';
        if (icon) {
            icon.className = 'fas fa-check-circle me-2';
        }
        if (btn) {
            btn.className = 'btn btn-success';
        }
    } else {
        header.style.background = 'linear-gradient(180deg, #f44336 0%, #da190b 100%)';
        if (icon) {
            icon.className = 'fas fa-exclamation-circle me-2';
        }
        if (btn) {
            btn.className = 'btn btn-danger';
        }
    }
    
    // Handle callback when modal is closed
    if (callback) {
        modal.addEventListener('hidden.bs.modal', function onModalHidden() {
            callback();
            modal.removeEventListener('hidden.bs.modal', onModalHidden);
        });
    }
    
    modalInstance.show();
}

/**
 * Show success message
 * @param {string} message - Success message
 * @param {function} callback - Optional callback
 */
function showSuccess(message, callback = null) {
    showMessage('Success!', message, true, callback);
}

/**
 * Show error message
 * @param {string} message - Error message
 * @param {function} callback - Optional callback
 */
function showError(message, callback = null) {
    showMessage('Error', message, false, callback);
}

/**
 * Show validation error message
 * @param {string} message - Validation error message
 */
function showValidationError(message) {
    showMessage('Validation Error', message, false);
}

/**
 * Show success message and reload page
 * @param {string} message - Success message
 * @param {number} delay - Delay before reload in milliseconds (default: 1500)
 */
function showSuccessAndReload(message, delay = 1500) {
    showSuccess(message, () => {
        setTimeout(() => location.reload(), delay);
    });
}

/**
 * Show success message and redirect
 * @param {string} message - Success message
 * @param {string} url - URL to redirect to
 * @param {number} delay - Delay before redirect in milliseconds (default: 1500)
 */
function showSuccessAndRedirect(message, url, delay = 1500) {
    showSuccess(message, () => {
        setTimeout(() => window.location.href = url, delay);
    });
}

/**
 * Show confirmation modal
 * @param {string} title - Title of the confirmation modal
 * @param {string} message - Message content of the confirmation modal
 * @param {function} onConfirm - Callback function when confirmed
 * @param {function} onCancel - Callback function when cancelled
 */
function showConfirmation(title, message, onConfirm, onCancel) {
    const modal = new bootstrap.Modal(document.getElementById('globalMessageModal'));
    const modalTitle = document.getElementById('globalMessageModalLabel');
    const modalBody = document.querySelector('#globalMessageModal .modal-body');
    const modalHeader = document.querySelector('#globalMessageModal .modal-header');
    const okButton = document.querySelector('#globalMessageModal .btn-primary');
    
    // Set warning style (orange/yellow)
    modalHeader.style.background = 'linear-gradient(180deg, #F59E0B 0%, #D97706 100%)';
    modalHeader.style.color = 'white';
    
    modalTitle.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ' + title;
    modalBody.innerHTML = message;
    
    // Remove any existing click handlers
    const newOkButton = okButton.cloneNode(true);
    okButton.parentNode.replaceChild(newOkButton, okButton);
    
    // Add confirm handler
    newOkButton.addEventListener('click', function() {
        modal.hide();
        if (onConfirm) onConfirm();
    });
    
    // Add cancel handler
    modal._element.addEventListener('hidden.bs.modal', function() {
        if (onCancel) onCancel();
    }, { once: true });
    
    modal.show();
}

/**
 * Handle AJAX form submission with styled messages
 * @param {string} url - Form submission URL
 * @param {FormData} formData - Form data to submit
 * @param {function} successCallback - Callback on success
 * @param {function} errorCallback - Callback on error
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
            showSuccess(message);
            if (successCallback) {
                setTimeout(successCallback, 1500);
            }
        } else {
            const error = data.error || 'An error occurred';
            showError(error);
            if (errorCallback) {
                errorCallback(data);
            }
        }
    })
    .catch(error => {
        showError('An unexpected error occurred: ' + error.message);
        if (errorCallback) {
            errorCallback(error);
        }
    });
}

// Make functions globally available
window.showMessage = showMessage;
window.showSuccess = showSuccess;
window.showError = showError;
window.showValidationError = showValidationError;
window.showSuccessAndReload = showSuccessAndReload;
window.showSuccessAndRedirect = showSuccessAndRedirect;
window.submitFormWithMessage = submitFormWithMessage;
