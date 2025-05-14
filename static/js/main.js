/**
 * Main JavaScript for Task Management Application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips using vanilla JS
    const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
    if (tooltips.length > 0) {
        Array.from(tooltips).forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
    }

    // Initialize Bootstrap popovers using vanilla JS
    const popovers = document.querySelectorAll('[data-toggle="popover"]');
    if (popovers.length > 0) {
        Array.from(popovers).forEach(popover => {
            new bootstrap.Popover(popover);
        });
    }
    
    // Sidebar toggle - works for both desktop and mobile
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const content = document.querySelector('.content');
    const header = document.querySelector('.header');
    
    if (sidebarToggle && sidebar) {
        // Remove existing event listeners (to avoid duplicates)
        const sidebarToggleClone = sidebarToggle.cloneNode(true);
        if (sidebarToggle.parentNode) {
            sidebarToggle.parentNode.replaceChild(sidebarToggleClone, sidebarToggle);
        }
        
        // Add the event listener to the clone
        sidebarToggleClone.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (window.innerWidth <= 768) {
                // Mobile behavior - show/hide sidebar
                sidebar.classList.toggle('mobile-show');
            } else {
                // Desktop behavior - collapse/expand sidebar
                sidebar.classList.toggle('collapsed');
                
                // Save state to localStorage
                const isCollapsed = sidebar.classList.contains('collapsed');
                localStorage.setItem('sidebar-collapsed', isCollapsed);
            }
        });
        
        // Close sidebar when clicking on content (for mobile)
        if (content) {
            content.addEventListener('click', function() {
                if (window.innerWidth <= 768 && sidebar.classList.contains('mobile-show')) {
                    sidebar.classList.remove('mobile-show');
                }
            });
        }
        
        // Check if sidebar was collapsed from previous visit (for desktop)
        if (window.innerWidth > 768) {
            const wasCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
            if (wasCollapsed) {
                sidebar.classList.add('collapsed');
            }
        }
        
        // Handle window resize - adjust sidebar state appropriately
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                // Switching from mobile to desktop
                sidebar.classList.remove('mobile-show');
                
                // Check saved desktop state
                const wasCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
                if (wasCollapsed) {
                    sidebar.classList.add('collapsed');
                } else {
                    sidebar.classList.remove('collapsed');
                }
            } else {
                // Switching from desktop to mobile
                sidebar.classList.remove('collapsed');
            }
        });
    }
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Auto-hiding alerts
    const autoHideAlerts = document.querySelectorAll('.alert-autohide');
    
    autoHideAlerts.forEach(alert => {
        setTimeout(() => {
            $(alert).fadeOut('slow', function() {
                $(this).remove();
            });
        }, 5000);
    });
    
    // Confirmation dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Show toast messages
    function showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            const newContainer = document.createElement('div');
            newContainer.className = 'toast-container';
            document.body.appendChild(newContainer);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast bg-${type} text-white`;
        toast.innerHTML = `
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.querySelector('.toast-container').appendChild(toast);
        
        $(toast).toast({
            delay: 5000,
            autohide: true
        });
        
        $(toast).toast('show');
        
        $(toast).on('hidden.bs.toast', function() {
            $(this).remove();
        });
    }
    
    // Make showToast available globally
    window.showToast = showToast;
    
    // Format dates to relative time
    function timeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        
        if (diffSec < 60) {
            return 'just now';
        }
        
        const diffMin = Math.floor(diffSec / 60);
        if (diffMin < 60) {
            return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
        }
        
        const diffHour = Math.floor(diffMin / 60);
        if (diffHour < 24) {
            return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
        }
        
        const diffDay = Math.floor(diffHour / 24);
        if (diffDay < 7) {
            return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
        }
        
        const diffWeek = Math.floor(diffDay / 7);
        if (diffWeek < 4) {
            return `${diffWeek} week${diffWeek > 1 ? 's' : ''} ago`;
        }
        
        const diffMonth = Math.floor(diffDay / 30);
        if (diffMonth < 12) {
            return `${diffMonth} month${diffMonth > 1 ? 's' : ''} ago`;
        }
        
        const diffYear = Math.floor(diffDay / 365);
        return `${diffYear} year${diffYear > 1 ? 's' : ''} ago`;
    }
    
    // Make timeAgo available globally
    window.timeAgo = timeAgo;
    
    // Format all time elements with data-timeago attribute
    const timeElements = document.querySelectorAll('[data-timeago]');
    
    timeElements.forEach(element => {
        const timestamp = element.getAttribute('data-timeago');
        element.textContent = timeAgo(timestamp);
    });
});