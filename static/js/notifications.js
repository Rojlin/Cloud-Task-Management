/**
 * Notifications JavaScript for Task Management Application
 */

let notificationSocket;
let notificationBadge;
let notificationDropdown;

document.addEventListener('DOMContentLoaded', function() {
    initNotifications();
});

/**
 * Initialize notifications functionality
 */
function initNotifications() {
    // Get notification elements
    notificationBadge = document.getElementById('notification-count');
    notificationDropdown = document.querySelector('.notification-dropdown');
    
    console.log('Notification badge element:', notificationBadge);
    console.log('Notification dropdown element:', notificationDropdown);
    
    // Connect to WebSocket for real-time notifications
    connectNotificationWebSocket();
    
    // Initial fetch of unread notification count
    fetchUnreadNotificationsCount();
    
    // Load notifications into the dropdown immediately
    if (notificationDropdown) {
        console.log('Loading notifications on page load...');
        loadNotificationsDropdown();
    }
    
    // Setup event listeners
    setupNotificationEventListeners();
}

/**
 * Connect to WebSocket for real-time notifications
 */
function connectNotificationWebSocket() {
    // Only connect if user is authenticated
    // Check if we can access the unread count API without redirect
    fetch('/notifications/api/unread-count/')
        .then(response => {
            // If we got a valid response (not redirected to login)
            if (response.ok) {
                // Close existing socket if any
                if (notificationSocket) {
                    notificationSocket.close();
                }
                
                // Create new WebSocket connection
                const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
                const wsUrl = `${protocol}://${window.location.host}/ws/notifications/`;
                
                notificationSocket = new WebSocket(wsUrl);
                
                notificationSocket.onopen = function(e) {
                    console.log('Notification WebSocket connected');
                };
                
                notificationSocket.onmessage = function(e) {
                    const data = JSON.parse(e.data);
                    handleNotification(data);
                };
                
                notificationSocket.onclose = function(e) {
                    console.log('Notification WebSocket disconnected', e);
                    
                    // Try to reconnect after a delay
                    setTimeout(() => {
                        connectNotificationWebSocket();
                    }, 3000);
                };
                
                notificationSocket.onerror = function(e) {
                    console.error('Notification WebSocket error:', e);
                };
            } else {
                console.log('User not authenticated, not connecting WebSocket');
            }
        })
        .catch(error => {
            console.error('Error checking authentication status:', error);
        });
}

/**
 * Handle incoming notification
 * @param {Object} data - The notification data
 */
function handleNotification(data) {
    console.log('Notification data received:', data);
    
    // Handle the notification if there's notification data (no matter what type)
    if (data.notification) {
        // Update notification count
        updateNotificationBadge(data.unread_count !== undefined ? data.unread_count : null);
        
        // Determine the toast type based on notification_type (if available)
        let toastType = 'info';
        if (data.notification.notification_type) {
            switch(data.notification.notification_type) {
                case 'task_updated':
                case 'task_assigned':
                    toastType = 'primary';
                    break;
                case 'project_created':
                case 'project_updated':
                    toastType = 'success';
                    break;
                case 'chat_message':
                    toastType = 'info';
                    break;
                default:
                    toastType = 'info';
            }
        }
        
        // Show toast notification
        showToast(data.notification.message, toastType);
        
        // Always add to dropdown when notification is received
        if (notificationDropdown) {
            console.log('Adding new notification to dropdown immediately');
            addNotificationToDropdown(data.notification);
        }
    } else if (data.unread_count !== undefined) {
        // Just update the badge if only count received
        updateNotificationBadge(data.unread_count);
    } else if (data.message) {
        // Process the message format notifications
        console.log('Processing message format notification:', data.message);
        
        // Create a notification object
        const notification = {
            id: Date.now(), // Generate a temporary ID
            title: data.message.title || 'New Notification',
            message: data.message.content || '',
            link: data.message.link || '#',
            is_read: false,
            created_at: new Date().toISOString()
        };
        
        // Show toast notification
        showToast(notification.message, 'info');
        
        // Always add to dropdown when notification is received
        if (notificationDropdown) {
            console.log('Adding message notification to dropdown immediately');
            addNotificationToDropdown(notification);
        }
        
        // Fetch updated count
        fetchUnreadNotificationsCount();
    }
}

/**
 * Fetch unread notification count from the server
 */
function fetchUnreadNotificationsCount() {
    fetch('/notifications/api/unread-count/')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateNotificationBadge(data.count);
        })
        .catch(error => {
            console.error('Error fetching notification count:', error);
        });
}

/**
 * Update the notification badge count
 * @param {number} count - The number of unread notifications
 */
function updateNotificationBadge(count) {
    if (!notificationBadge) return;
    
    console.log('Updating notification badge count:', count);
    
    // If count is null, fetch it from the server
    if (count === null) {
        fetchUnreadNotificationsCount();
        return;
    }
    
    if (count > 0) {
        notificationBadge.textContent = count > 99 ? '99+' : count;
        notificationBadge.classList.remove('d-none');
        
        // Also update any other notification indicators
        const allBadges = document.querySelectorAll('.notification-badge');
        allBadges.forEach(badge => {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('d-none');
        });
    } else {
        notificationBadge.classList.add('d-none');
        
        // Also update any other notification indicators
        const allBadges = document.querySelectorAll('.notification-badge');
        allBadges.forEach(badge => {
            badge.classList.add('d-none');
        });
    }
}

/**
 * Setup notification event listeners
 */
function setupNotificationEventListeners() {
    // Mark notification as read
    const notificationItems = document.querySelectorAll('.notification-item[data-notification-id]');
    
    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            const notificationId = this.getAttribute('data-notification-id');
            markNotificationAsRead(notificationId);
        });
    });
    
    // Mark all notifications as read
    const markAllReadButton = document.querySelector('.mark-all-read-button');
    
    if (markAllReadButton) {
        markAllReadButton.addEventListener('click', function(e) {
            e.preventDefault();
            markAllNotificationsAsRead();
        });
    }
    
    // Toggle notification dropdown
    const notificationToggle = document.querySelector('.btn.btn-light.position-relative.dropdown-toggle');
    
    if (notificationToggle && notificationDropdown) {
        notificationToggle.addEventListener('click', function() {
            // Load notifications when dropdown is clicked
            loadNotificationsDropdown();
        });
        
        // Also load when dropdown is shown (for Bootstrap events)
        notificationToggle.addEventListener('shown.bs.dropdown', function() {
            loadNotificationsDropdown();
        });
    }
}

/**
 * Mark a notification as read
 * @param {string} notificationId - The ID of the notification
 */
function markNotificationAsRead(notificationId) {
    fetch(`/notifications/${notificationId}/mark-read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Update the notification badge
        updateNotificationBadge(data.unread_count);
        
        // Update UI if on notifications page
        const notificationItem = document.querySelector(`.notification-item[data-notification-id="${notificationId}"]`);
        if (notificationItem) {
            notificationItem.classList.remove('unread');
        }
    })
    .catch(error => {
        console.error('Error marking notification as read:', error);
    });
}

/**
 * Mark all notifications as read
 */
function markAllNotificationsAsRead() {
    fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Update the notification badge
        updateNotificationBadge(0);
        
        // Update UI if on notifications page
        document.querySelectorAll('.notification-item.unread').forEach(item => {
            item.classList.remove('unread');
        });
        
        showToast('All notifications marked as read', 'success');
    })
    .catch(error => {
        console.error('Error marking all notifications as read:', error);
        showToast('Failed to mark notifications as read', 'error');
    });
}

/**
 * Load notifications into the dropdown menu
 */
function loadNotificationsDropdown() {
    if (!notificationDropdown) {
        console.error('Notification dropdown element not found');
        return;
    }
    
    const notificationList = notificationDropdown.querySelector('.notification-list');
    
    if (!notificationList) {
        console.error('Notification list element not found within dropdown');
        return;
    }
    
    // Show loading indicator
    notificationList.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm" role="status"></div><span class="ms-2">Loading notifications...</span></div>';
    
    console.log('Fetching recent notifications...');
    
    fetch('/notifications/api/recent/')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Received notifications data:', data);
            
            if (data.notifications && data.notifications.length > 0) {
                notificationList.innerHTML = '';
                
                data.notifications.forEach(notification => {
                    // Debug each notification
                    console.log('Processing notification:', notification);
                    addNotificationToDropdown(notification);
                });
            } else {
                notificationList.innerHTML = '<div class="text-center py-3">No notifications</div>';
            }
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
            notificationList.innerHTML = '<div class="text-center py-3 text-danger">Failed to load notifications</div>';
        });
}

/**
 * Add a notification to the dropdown menu
 * @param {Object} notification - The notification object
 */
function addNotificationToDropdown(notification) {
    if (!notificationDropdown) {
        console.error('Notification dropdown element not found when adding notification');
        return;
    }
    
    const notificationList = notificationDropdown.querySelector('.notification-list');
    
    if (!notificationList) {
        console.error('Notification list element not found when adding notification');
        return;
    }
    
    console.log('Adding notification to dropdown:', notification);
    
    // Check if notification already exists in the dropdown
    const existingNotification = notificationList.querySelector(`[data-notification-id="${notification.id}"]`);
    if (existingNotification) {
        console.log('Notification already exists in dropdown, not adding duplicate');
        return;
    }
    
    // Create a new notification item
    const notificationItem = document.createElement('div');
    notificationItem.classList.add('notification-item');
    
    if (!notification.is_read) {
        notificationItem.classList.add('unread');
    }
    
    notificationItem.setAttribute('data-notification-id', notification.id);
    
    let notificationContent = '';
    
    // Different format based on notification type
    if (notification.notification_type === 'chat_message') {
        // For chat messages, format with the "New" badge as shown in screenshot
        const roomName = notification.title.split(' in ')[1] || '';
        
        notificationContent = `
            <div class="position-relative w-100">
                <div class="d-flex align-items-center mb-1">
                    <div class="notification-icon me-2">
                        <i class="fas fa-comment text-info"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-bold">New message in ${roomName}</div>
                    </div>
                    <span class="badge bg-info position-absolute" style="top: 0; right: 0;">New</span>
                </div>
                <div class="ps-4 notification-text">${notification.message}</div>
                <div class="ps-4 notification-time">${timeAgo(notification.created_at)}</div>
            </div>
        `;
    } else {
        // Default format for other notification types
        let iconClass = 'bell';
        
        // Set icon based on notification type
        switch(notification.notification_type) {
            case 'task_assigned':
            case 'task_updated':
            case 'task_commented':
                iconClass = 'tasks';
                break;
            case 'project_created':
            case 'project_updated':
            case 'project_member_added':
                iconClass = 'project-diagram';
                break;
            case 'system':
                iconClass = 'cog';
                break;
        }
        
        notificationContent = `
            <div class="notification-icon">
                <i class="fas fa-${iconClass}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-title">${notification.title}</div>
                <div class="notification-text">${notification.message}</div>
                <div class="notification-time">${timeAgo(notification.created_at)}</div>
            </div>
        `;
    }
    
    // Set the HTML content
    notificationItem.innerHTML = notificationContent;
    
    // Add click handler
    notificationItem.addEventListener('click', function() {
        markNotificationAsRead(notification.id);
        
        if (notification.link) {
            window.location.href = notification.link;
        }
    });
    
    // Add to the top of the list
    if (notificationList.firstChild) {
        notificationList.insertBefore(notificationItem, notificationList.firstChild);
    } else {
        notificationList.appendChild(notificationItem);
    }
    
    // Make sure the notification count is updated
    fetchUnreadNotificationsCount();
}

/**
 * Get CSRF token from cookies
 * @returns {string} The CSRF token
 */
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    
    return cookieValue;
}

/**
 * Format a date as a human-readable time ago string
 * @param {string} dateString - ISO date string
 * @returns {string} Human-readable time ago
 */
function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    // Less than a minute
    if (seconds < 60) {
        return 'just now';
    }
    
    // Less than an hour
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    }
    
    // Less than a day
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    }
    
    // Less than a week
    const days = Math.floor(hours / 24);
    if (days < 7) {
        return `${days} day${days > 1 ? 's' : ''} ago`;
    }
    
    // Format as date
    return date.toLocaleDateString();
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, info, warning, error)
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast show border-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.id = toastId;
    
    // Get appropriate icon for the toast type
    let icon = 'info-circle';
    switch (type) {
        case 'success':
            icon = 'check-circle';
            break;
        case 'warning':
            icon = 'exclamation-triangle';
            break;
        case 'error':
            icon = 'exclamation-circle';
            break;
    }
    
    // Set toast content
    toast.innerHTML = `
        <div class="toast-header bg-${type} bg-opacity-10">
            <i class="fas fa-${icon} me-2 text-${type}"></i>
            <strong class="me-auto">Notification</strong>
            <small>Just now</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (document.getElementById(toastId)) {
            const bsToast = new bootstrap.Toast(document.getElementById(toastId));
            bsToast.hide();
        }
    }, 5000);
    
    // Handle close button
    const closeButton = toast.querySelector('.btn-close');
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            toast.remove();
        });
    }
}
