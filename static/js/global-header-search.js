/**
 * Global Header Search & In-Page Real-Time Filtering
 * Provides:
 * 1. Real-time in-page table filtering as you type (only when table rows exist)
 * 2. In-input match count badge & 1-click clear (Esc)
 * 3. Command palette & Quick navigation dropdown with detached absolute positioning
 * 4. Fast AJAX backend search preview for 2+ character queries
 * 5. Keyboard shortcut (Ctrl+K or /)
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('headerSearchForm');
        const input = document.getElementById('globalSearch');
        const dropdown = document.getElementById('globalSearchDropdown');
        const filterBadge = document.getElementById('pageFilterBadge');
        const clearBtn = document.getElementById('clearSearchBtn');

        if (!form || !input) return;

        const role = form.dataset.userRole || '';
        const schoolSlug = form.dataset.schoolSlug || '';
        const searchApiUrl = form.dataset.searchApi || '';

        let ajaxTimer = null;
        let activeDropdownIndex = -1;

        // Static ERP Quick Navigation Catalog
        const superadminPages = [
            { title: 'Database Backups', desc: 'Master & tenant DB backups, downloads', url: '/superadmin/backups/', icon: 'fas fa-database', category: 'System' },
            { title: 'School Tenants', desc: 'Manage all school instances', url: '/superadmin/schools/', icon: 'fas fa-school', category: 'Tenants' },
            { title: 'Register New School', desc: 'Provision a new school tenant', url: '/superadmin/schools/create/', icon: 'fas fa-plus-circle', category: 'Tenants' },
            { title: 'School Administrators', desc: 'Manage admin user accounts', url: '/superadmin/admins/', icon: 'fas fa-user-shield', category: 'Users' },
            { title: 'Subscriptions & Plans', desc: 'Tenant billing packages & pricing', url: '/superadmin/subscriptions/', icon: 'fas fa-credit-card', category: 'Billing' },
            { title: 'Global Settings & Branding', desc: 'System colors, logos, defaults', url: '/superadmin/settings/', icon: 'fas fa-sliders-h', category: 'Settings' },
            { title: 'System Maintenance', desc: 'Maintenance mode toggle & status', url: '/superadmin/settings/maintenance/', icon: 'fas fa-tools', category: 'Settings' },
            { title: 'SMS Gateways', desc: 'SMS provider configurations', url: '/superadmin/settings/sms/', icon: 'fas fa-sms', category: 'Integrations' },
            { title: 'Email (SMTP) Gateways', desc: 'Outgoing email server settings', url: '/superadmin/settings/email/', icon: 'fas fa-envelope', category: 'Integrations' },
            { title: 'Database Configurations', desc: 'Global database connection hosts', url: '/superadmin/settings/database/', icon: 'fas fa-server', category: 'Settings' },
            { title: 'Payment Gateways', desc: 'Stripe, PayPal, Bank configs', url: '/superadmin/payment-config/', icon: 'fas fa-wallet', category: 'Billing' },
            { title: 'Payment Approvals', desc: 'Verify manual bank transfers', url: '/superadmin/payments/approval/', icon: 'fas fa-check-double', category: 'Billing' },
            { title: 'Platform Invoices', desc: 'Tenant subscription invoices', url: '/superadmin/invoices/', icon: 'fas fa-file-invoice-dollar', category: 'Billing' },
            { title: 'Audit Logs', desc: 'Security trails and administrative logs', url: '/superadmin/logs/', icon: 'fas fa-shield-alt', category: 'Security' },
            { title: 'Homepage CMS', desc: 'Landing page content management', url: '/superadmin/content/homepage/', icon: 'fas fa-globe', category: 'Content' },
            { title: 'Dashboard', desc: 'Superadmin analytics & stats', url: '/superadmin/', icon: 'fas fa-tachometer-alt', category: 'Overview' }
        ];

        const schoolPages = schoolSlug ? [
            { title: 'Students Directory', desc: 'Manage student enrollments & profiles', url: `/school/${schoolSlug}/students/`, icon: 'fas fa-user-graduate', category: 'Students' },
            { title: 'Admit New Student', desc: 'Register a new student', url: `/school/${schoolSlug}/students/add/`, icon: 'fas fa-user-plus', category: 'Students' },
            { title: 'Parents & Guardians', desc: 'Parent contact information', url: `/school/${schoolSlug}/students/parents/`, icon: 'fas fa-user-friends', category: 'Students' },
            { title: 'Classes & Sections', desc: 'Manage class sections and teachers', url: `/school/${schoolSlug}/academics/classes/`, icon: 'fas fa-chalkboard', category: 'Academics' },
            { title: 'Subjects Directory', desc: 'Academic courses and subjects', url: `/school/${schoolSlug}/academics/subjects/`, icon: 'fas fa-book', category: 'Academics' },
            { title: 'Teachers & Staff', desc: 'Faculty directory and employees', url: `/school/${schoolSlug}/hr/staff/`, icon: 'fas fa-chalkboard-teacher', category: 'HR' },
            { title: 'Daily Attendance', desc: 'Record student and staff attendance', url: `/school/${schoolSlug}/attendance/`, icon: 'fas fa-clipboard-check', category: 'Attendance' },
            { title: 'Fees Management', desc: 'Collect fees and manage invoices', url: `/school/${schoolSlug}/fees/`, icon: 'fas fa-money-bill-wave', category: 'Finance' },
            { title: 'Fee Invoices', desc: 'View student fee invoices', url: `/school/${schoolSlug}/fees/invoices/`, icon: 'fas fa-file-invoice-dollar', category: 'Finance' },
            { title: 'Exams & Results', desc: 'Exam schedules and report cards', url: `/school/${schoolSlug}/examinations/`, icon: 'fas fa-file-alt', category: 'Examinations' },
            { title: 'Library Books', desc: 'Catalog, book issues, and returns', url: `/school/${schoolSlug}/library/`, icon: 'fas fa-book-reader', category: 'Library' },
            { title: 'Transport & Routes', desc: 'School buses and transit routes', url: `/school/${schoolSlug}/transport/`, icon: 'fas fa-bus', category: 'Transport' },
            { title: 'Dormitory & Hostels', desc: 'Rooms, beds, and student allocations', url: `/school/${schoolSlug}/dormitory/`, icon: 'fas fa-hotel', category: 'Dormitory' },
            { title: 'Notices & Circulars', desc: 'Broadcast announcements and SMS', url: `/school/${schoolSlug}/communication/notices/`, icon: 'fas fa-bullhorn', category: 'Communication' },
            { title: 'School Database Backups', desc: 'Create and download school DB backups', url: `/school/${schoolSlug}/backups/`, icon: 'fas fa-database', category: 'System' },
            { title: 'School Settings', desc: 'Academic years, grading scale, branding', url: `/school/${schoolSlug}/settings/`, icon: 'fas fa-cog', category: 'Settings' },
            { title: 'Dashboard', desc: 'School overview and metrics', url: `/school/${schoolSlug}/`, icon: 'fas fa-tachometer-alt', category: 'Overview' }
        ] : [];

        const defaultCatalog = (role === 'superadmin' || role === 'super_admin') ? superadminPages : schoolPages;

        // -------------------------------------------------------------
        // 1. In-Page Real-time Table Filtering Engine
        // -------------------------------------------------------------
        function filterContentOnCurrentPage(query) {
            const cleanQuery = query.trim().toLowerCase();
            const terms = cleanQuery.split(/\s+/).filter(Boolean);

            let totalRowsFound = 0;
            let totalRowsMatched = 0;
            const matchingSnippets = [];

            // Select active/visible tables only in content area
            const tables = document.querySelectorAll(
                '.content-container table tbody, .main-content table tbody, .tab-pane.active table tbody, table.table tbody'
            );

            tables.forEach(tbody => {
                // Ignore search results dropdown, calculator, or modal tables
                if (tbody.closest('#globalSearchDropdown') || tbody.closest('.modal')) return;

                const rows = tbody.querySelectorAll('tr:not(.search-empty-state-row):not(.table-header-row)');
                if (!rows.length) return;

                let tableHasMatch = false;

                rows.forEach(row => {
                    totalRowsFound++;
                    if (!cleanQuery) {
                        row.style.display = '';
                        return;
                    }

                    const text = (row.innerText || row.textContent || '').toLowerCase();
                    const matches = terms.every(term => text.includes(term));

                    if (matches) {
                        row.style.display = '';
                        totalRowsMatched++;
                        tableHasMatch = true;

                        // Grab snippet for dropdown preview
                        if (matchingSnippets.length < 3) {
                            const firstCol = row.querySelector('td:not(:empty)');
                            const snippetText = firstCol ? firstCol.innerText.trim().split('\n')[0] : '';
                            if (snippetText && !matchingSnippets.some(s => s.element === row)) {
                                matchingSnippets.push({
                                    title: snippetText,
                                    element: row
                                });
                            }
                        }
                    } else {
                        row.style.display = 'none';
                    }
                });

                // Empty state message per table (only if the table originally had rows)
                let emptyRow = tbody.querySelector('.search-empty-state-row');
                if (cleanQuery && !tableHasMatch && totalRowsFound > 0) {
                    if (!emptyRow) {
                        emptyRow = document.createElement('tr');
                        emptyRow.className = 'search-empty-state-row';
                        const colCount = tbody.closest('table').querySelectorAll('thead th').length || 6;
                        emptyRow.innerHTML = `
                            <td colspan="${colCount}" class="text-center py-3 text-muted" style="font-size: 13px;">
                                <i class="fas fa-search me-2 opacity-50"></i>No rows matching "<strong>${escapeHtml(query)}</strong>" in this table
                            </td>
                        `;
                        tbody.appendChild(emptyRow);
                    } else {
                        emptyRow.style.display = '';
                        const strong = emptyRow.querySelector('strong');
                        if (strong) strong.textContent = query;
                    }
                } else if (emptyRow) {
                    emptyRow.style.display = 'none';
                }
            });

            // Update match count badge and clear button
            if (cleanQuery) {
                if (clearBtn) clearBtn.classList.remove('d-none');
                if (filterBadge) {
                    if (totalRowsFound > 0) {
                        filterBadge.classList.remove('d-none');
                        filterBadge.textContent = `${totalRowsMatched} on page`;
                        filterBadge.className = totalRowsMatched > 0 
                            ? 'search-filter-badge d-inline-flex align-items-center' 
                            : 'search-filter-badge text-danger border-danger-subtle bg-danger-subtle d-inline-flex align-items-center';
                    } else {
                        filterBadge.classList.add('d-none');
                    }
                }
            } else {
                if (clearBtn) clearBtn.classList.add('d-none');
                if (filterBadge) filterBadge.classList.add('d-none');
            }

            return {
                matchedCount: totalRowsMatched,
                snippets: matchingSnippets
            };
        }

        function resetInPageFilter() {
            input.value = '';
            filterContentOnCurrentPage('');
            closeDropdown();
            input.focus();
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                resetInPageFilter();
            });
        }

        // -------------------------------------------------------------
        // 2. Command Palette & Dropdown Renderer
        // -------------------------------------------------------------
        function renderDropdown(data) {
            const { query, matchedPages, onPageMatches, apiResults } = data;
            if (!query) {
                closeDropdown();
                return;
            }

            let html = '';
            let itemCount = 0;

            // Section 1: "On This Page" matching items
            if (onPageMatches && onPageMatches.snippets && onPageMatches.snippets.length > 0) {
                html += `
                    <div class="search-dropdown-section">
                        <div class="search-dropdown-header">
                            <span>Matches on Page (${onPageMatches.matchedCount})</span>
                        </div>
                `;
                onPageMatches.snippets.forEach((item, idx) => {
                    html += `
                        <div class="search-dropdown-item jump-to-row-item" data-idx="${itemCount++}" data-snippet-idx="${idx}">
                            <div class="search-item-content">
                                <div class="search-item-title">${escapeHtml(item.title)}</div>
                                <div class="search-item-subtitle">Scroll to row on page</div>
                            </div>
                            <span class="search-item-badge">On Page</span>
                        </div>
                    `;
                });
                html += `</div>`;
            }

            // Section 2: "ERP Modules & Pages"
            if (matchedPages && matchedPages.length > 0) {
                html += `
                    <div class="search-dropdown-section">
                        <div class="search-dropdown-header">
                            <span>ERP Modules & Pages</span>
                        </div>
                `;
                matchedPages.forEach(p => {
                    html += `
                        <a href="${p.url}" class="search-dropdown-item" data-idx="${itemCount++}">
                            <div class="search-item-content">
                                <div class="search-item-title">${escapeHtml(p.title)}</div>
                                <div class="search-item-subtitle">${escapeHtml(p.desc)}</div>
                            </div>
                            <span class="search-item-badge">${escapeHtml(p.category || 'Page')}</span>
                        </a>
                    `;
                });
                html += `</div>`;
            }

            // Section 3: Live AJAX Results (Schools, Users, Backups, Students, etc.)
            if (apiResults) {
                const { schools, users, backups, students, staff, classes } = apiResults;

                // Schools (max 3)
                if (schools && schools.length > 0) {
                    html += `<div class="search-dropdown-section"><div class="search-dropdown-header"><span>Schools</span></div>`;
                    schools.slice(0, 3).forEach(s => {
                        html += `
                            <a href="${s.url}" class="search-dropdown-item" data-idx="${itemCount++}">
                                <div class="search-item-content">
                                    <div class="search-item-title">${escapeHtml(s.title)}</div>
                                    <div class="search-item-subtitle">${escapeHtml(s.subtitle)}</div>
                                </div>
                                <span class="search-item-badge">School</span>
                            </a>
                        `;
                    });
                    html += `</div>`;
                }

                // Users (max 3)
                if (users && users.length > 0) {
                    html += `<div class="search-dropdown-section"><div class="search-dropdown-header"><span>Administrators</span></div>`;
                    users.slice(0, 3).forEach(u => {
                        html += `
                            <a href="${u.url}" class="search-dropdown-item" data-idx="${itemCount++}">
                                <div class="search-item-content">
                                    <div class="search-item-title">${escapeHtml(u.title)}</div>
                                    <div class="search-item-subtitle">${escapeHtml(u.subtitle)}</div>
                                </div>
                                <span class="search-item-badge">${escapeHtml(u.badge || 'Admin')}</span>
                            </a>
                        `;
                    });
                    html += `</div>`;
                }

                // Backups (max 3)
                if (backups && backups.length > 0) {
                    html += `<div class="search-dropdown-section"><div class="search-dropdown-header"><span>Database Backups</span></div>`;
                    backups.slice(0, 3).forEach(b => {
                        html += `
                            <a href="${b.url}" class="search-dropdown-item" data-idx="${itemCount++}">
                                <div class="search-item-content">
                                    <div class="search-item-title">${escapeHtml(b.title)}</div>
                                    <div class="search-item-subtitle">${escapeHtml(b.subtitle)}</div>
                                </div>
                                <span class="search-item-badge">Backup</span>
                            </a>
                        `;
                    });
                    html += `</div>`;
                }

                // Students (School context, max 3)
                if (students && students.length > 0) {
                    html += `<div class="search-dropdown-section"><div class="search-dropdown-header"><span>Students</span></div>`;
                    students.slice(0, 3).forEach(s => {
                        html += `
                            <a href="${s.url}" class="search-dropdown-item" data-idx="${itemCount++}">
                                <div class="search-item-content">
                                    <div class="search-item-title">${escapeHtml(s.title)}</div>
                                    <div class="search-item-subtitle">${escapeHtml(s.subtitle)}</div>
                                </div>
                                <span class="search-item-badge">Student</span>
                            </a>
                        `;
                    });
                    html += `</div>`;
                }

                // Staff (School context, max 3)
                if (staff && staff.length > 0) {
                    html += `<div class="search-dropdown-section"><div class="search-dropdown-header"><span>Teachers & Staff</span></div>`;
                    staff.slice(0, 3).forEach(st => {
                        html += `
                            <a href="${st.url}" class="search-dropdown-item" data-idx="${itemCount++}">
                                <div class="search-item-content">
                                    <div class="search-item-title">${escapeHtml(st.title)}</div>
                                    <div class="search-item-subtitle">${escapeHtml(st.subtitle)}</div>
                                </div>
                                <span class="search-item-badge">Staff</span>
                            </a>
                        `;
                    });
                    html += `</div>`;
                }
            }

            // Footer with Enter reminder
            if (itemCount > 0) {
                html += `
                    <div class="search-dropdown-footer">
                        <span>Press <kbd>↵ Enter</kbd> to view full results</span>
                        <span><kbd>Esc</kbd> to clear</span>
                    </div>
                `;
                dropdown.innerHTML = html;
                dropdown.classList.remove('d-none');
                activeDropdownIndex = -1;

                // Bind click handler for "jump-to-row" items
                if (onPageMatches && onPageMatches.snippets) {
                    const jumpItems = dropdown.querySelectorAll('.jump-to-row-item');
                    jumpItems.forEach(el => {
                        const snippetIdx = parseInt(el.dataset.snippetIdx, 10);
                        const snippet = onPageMatches.snippets[snippetIdx];
                        if (snippet && snippet.element) {
                            el.addEventListener('click', function (e) {
                                e.preventDefault();
                                closeDropdown();
                                snippet.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                snippet.element.classList.add('row-highlight-pulse');
                                setTimeout(() => snippet.element.classList.remove('row-highlight-pulse'), 2500);
                            });
                        }
                    });
                }
            } else {
                dropdown.innerHTML = `
                    <div class="p-3 text-center text-muted" style="font-size: 12.5px;">
                        Press <kbd>Enter</kbd> to search platform for "${escapeHtml(query)}"
                    </div>
                `;
                dropdown.classList.remove('d-none');
            }
        }

        function closeDropdown() {
            if (dropdown) {
                dropdown.classList.add('d-none');
                dropdown.innerHTML = '';
            }
            activeDropdownIndex = -1;
        }

        // -------------------------------------------------------------
        // 3. Search Input Listeners & AJAX Orchestration
        // -------------------------------------------------------------
        input.addEventListener('input', function (e) {
            const query = e.target.value;
            const cleanQuery = query.trim();

            // 1. Instant on-page table filtering
            const onPageResults = filterContentOnCurrentPage(query);

            if (!cleanQuery) {
                closeDropdown();
                return;
            }

            // 2. Filter local catalog of navigation links (max 4)
            const qLower = cleanQuery.toLowerCase();
            const matchedPages = defaultCatalog.filter(p =>
                p.title.toLowerCase().includes(qLower) ||
                p.desc.toLowerCase().includes(qLower) ||
                (p.category && p.category.toLowerCase().includes(qLower))
            ).slice(0, 4);

            // Render immediate local feedback
            renderDropdown({
                query: cleanQuery,
                matchedPages: matchedPages,
                onPageMatches: onPageResults,
                apiResults: null
            });

            // 3. Debounced AJAX fetch for backend database records (only when 2+ chars)
            if (cleanQuery.length >= 2 && searchApiUrl && searchApiUrl !== '#') {
                clearTimeout(ajaxTimer);
                ajaxTimer = setTimeout(() => {
                    fetch(`${searchApiUrl}?q=${encodeURIComponent(cleanQuery)}`, {
                        headers: { 'X-Requested-With': 'XMLHttpRequest' }
                    })
                    .then(res => res.json())
                    .then(data => {
                        // Re-render dropdown with live records merged
                        renderDropdown({
                            query: cleanQuery,
                            matchedPages: matchedPages,
                            onPageMatches: onPageResults,
                            apiResults: data
                        });
                    })
                    .catch(() => {});
                }, 220);
            }
        });

        // -------------------------------------------------------------
        // 4. Keyboard Navigation & Shortcuts
        // -------------------------------------------------------------
        input.addEventListener('keydown', function (e) {
            const items = dropdown ? dropdown.querySelectorAll('.search-dropdown-item') : [];

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!items.length) return;
                activeDropdownIndex = (activeDropdownIndex + 1) % items.length;
                updateDropdownFocus(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (!items.length) return;
                activeDropdownIndex = (activeDropdownIndex - 1 + items.length) % items.length;
                updateDropdownFocus(items);
            } else if (e.key === 'Enter') {
                if (activeDropdownIndex >= 0 && items[activeDropdownIndex]) {
                    e.preventDefault();
                    items[activeDropdownIndex].click();
                }
                // Otherwise form submits naturally to full search page
            } else if (e.key === 'Escape') {
                e.preventDefault();
                resetInPageFilter();
            }
        });

        function updateDropdownFocus(items) {
            items.forEach((item, idx) => {
                if (idx === activeDropdownIndex) {
                    item.classList.add('active');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('active');
                }
            });
        }

        // Global hotkey: Ctrl+K or / to focus search
        document.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                input.focus();
                input.select();
            } else if (e.key === '/' && document.activeElement !== input) {
                const tag = (document.activeElement.tagName || '').toLowerCase();
                if (tag !== 'input' && tag !== 'textarea' && !document.activeElement.isContentEditable) {
                    e.preventDefault();
                    input.focus();
                    input.select();
                }
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!form.contains(e.target)) {
                closeDropdown();
            }
        });

        // Re-open dropdown when focusing if there is text
        input.addEventListener('focus', function () {
            if (input.value.trim().length > 0) {
                input.dispatchEvent(new Event('input'));
            }
        });

        function escapeHtml(text) {
            if (!text) return '';
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
    });
})();
