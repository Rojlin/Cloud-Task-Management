/**
 * Main JavaScript for Task Management Application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    $(function () {
        $('[data-toggle="tooltip"]').tooltip();
    });

    // Initialize Bootstrap popovers
    $(function () {
        $('[data-toggle="popover"]').popover();
    });
    
    // Sidebar toggle
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            document.body.classList.toggle('sidebar-collapsed');
            
            // Save state to localStorage
            const isCollapsed = document.body.classList.contains('sidebar-collapsed');
            localStorage.setItem('sidebar-collapsed', isCollapsed);
        });
        
        // Check if sidebar was collapsed from previous visit
        const wasCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
        if (wasCollapsed) {
            document.body.classList.add('sidebar-collapsed');
        }
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