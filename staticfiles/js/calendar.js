/**
 * Calendar JavaScript for Task Management Application
 */

let calendar;
let projectFilter;

document.addEventListener('DOMContentLoaded', function() {
    initTaskCalendar();
});

/**
 * Initialize the FullCalendar component
 */
function initTaskCalendar() {
    const calendarEl = document.getElementById('task-calendar');
    
    if (!calendarEl) {
        return; // Exit if no calendar element
    }
    
    // Get project ID if on project calendar page
    projectFilter = calendarEl.getAttribute('data-project-id');
    
    // Initialize FullCalendar
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listWeek'
        },
        themeSystem: 'bootstrap',
        events: loadCalendarEvents,
        eventClick: handleEventClick,
        dateClick: handleDateClick,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            meridiem: false
        },
        eventDidMount: function(info) {
            // Add tooltip with more information
            const tooltip = document.createElement('div');
            tooltip.className = 'calendar-tooltip';
            
            const eventData = info.event.extendedProps;
            tooltip.innerHTML = `
                <div class="tooltip-title">${info.event.title}</div>
                <div class="tooltip-content">
                    <p><strong>Status:</strong> ${eventData.status}</p>
                    <p><strong>Project:</strong> ${eventData.project}</p>
                    <p><strong>Assignee:</strong> ${eventData.assignee}</p>
                </div>
            `;
            
            new Popper(info.el, tooltip, {
                placement: 'top',
                modifiers: {
                    preventOverflow: {
                        enabled: true,
                        boundariesElement: 'viewport'
                    }
                }
            });
            
            // Show tooltip on hover
            info.el.addEventListener('mouseenter', function() {
                document.body.appendChild(tooltip);
            });
            
            // Hide tooltip when mouse leaves
            info.el.addEventListener('mouseleave', function() {
                if (document.body.contains(tooltip)) {
                    document.body.removeChild(tooltip);
                }
            });
        }
    });
    
    calendar.render();
    
    // Add event listeners for filter controls
    initCalendarFilters();
}

/**
 * Load calendar events from the server
 * @param {Object} info - Information object from FullCalendar
 * @param {function} successCallback - Callback for successful load
 * @param {function} failureCallback - Callback for failed load
 */
function loadCalendarEvents(info, successCallback, failureCallback) {
    // Build URL with filters
    let url = '/tasks/api/tasks/';
    
    if (projectFilter) {
        url += `?project_id=${projectFilter}`;
    }
    
    // Add date range filter
    const startDate = info.startStr;
    const endDate = info.endStr;
    
    if (url.includes('?')) {
        url += `&start=${startDate}&end=${endDate}`;
    } else {
        url += `?start=${startDate}&end=${endDate}`;
    }
    
    // Add any additional filters
    const statusFilter = document.querySelector('.calendar-status-filter')?.value;
    const priorityFilter = document.querySelector('.calendar-priority-filter')?.value;
    
    if (statusFilter) {
        url += `&status=${statusFilter}`;
    }
    
    if (priorityFilter) {
        url += `&priority=${priorityFilter}`;
    }
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            successCallback(data);
        })
        .catch(error => {
            console.error('Error loading calendar events:', error);
            failureCallback(error);
        });
}

/**
 * Handle click on a calendar event
 * @param {Object} info - Information about the clicked event
 */
function handleEventClick(info) {
    info.jsEvent.preventDefault();
    const eventUrl = info.event.url;
    
    if (eventUrl) {
        window.location.href = eventUrl;
    }
}

/**
 * Handle click on a calendar date
 * @param {Object} info - Information about the clicked date
 */
function handleDateClick(info) {
    // Show modal for quick task creation
    const modal = document.createElement('div');
    modal.classList.add('modal');
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Create Task for ${info.dateStr}</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <p>Would you like to create a new task due on this date?</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                    <a href="/tasks/create/?due_date=${info.dateStr}${projectFilter ? '&project=' + projectFilter : ''}" class="btn btn-primary">Create Task</a>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Handle close button
    modal.querySelector('[data-dismiss="modal"]').addEventListener('click', function() {
        document.body.removeChild(modal);
    });
    
    // Show modal
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

/**
 * Initialize calendar filter controls
 */
function initCalendarFilters() {
    const statusFilter = document.querySelector('.calendar-status-filter');
    const priorityFilter = document.querySelector('.calendar-priority-filter');
    const refreshButton = document.querySelector('.calendar-refresh-button');
    
    // Handle filter changes
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            calendar.refetchEvents();
        });
    }
    
    if (priorityFilter) {
        priorityFilter.addEventListener('change', function() {
            calendar.refetchEvents();
        });
    }
    
    // Handle refresh button
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            calendar.refetchEvents();
        });
    }
    
    // Handle today button
    const todayButton = document.querySelector('.calendar-today-button');
    if (todayButton) {
        todayButton.addEventListener('click', function() {
            calendar.today();
        });
    }
    
    // Handle view toggle buttons
    const viewButtons = document.querySelectorAll('.calendar-view-button');
    if (viewButtons.length > 0) {
        viewButtons.forEach(button => {
            button.addEventListener('click', function() {
                const view = this.getAttribute('data-view');
                calendar.changeView(view);
                
                // Update active state
                viewButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }
}

/**
 * Filter calendar events by search query
 * @param {string} query - Search query string
 */
function searchCalendarEvents(query) {
    if (!calendar) return;
    
    if (!query) {
        // Reset filtering
        calendar.getEvents().forEach(event => {
            event.setProp('display', 'auto');
        });
        return;
    }
    
    query = query.toLowerCase();
    
    // Filter events
    calendar.getEvents().forEach(event => {
        const title = event.title.toLowerCase();
        const project = event.extendedProps.project?.toLowerCase() || '';
        const assignee = event.extendedProps.assignee?.toLowerCase() || '';
        
        if (title.includes(query) || project.includes(query) || assignee.includes(query)) {
            event.setProp('display', 'auto');
        } else {
            event.setProp('display', 'none');
        }
    });
}

/**
 * Export calendar events to iCalendar format
 */
function exportCalendarEvents() {
    // Get all current events
    const events = calendar.getEvents();
    
    if (events.length === 0) {
        showToast('No events to export', 'warning');
        return;
    }
    
    // Build iCalendar content
    let icsContent = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Task Management App//Calendar//EN'
    ];
    
    events.forEach(event => {
        const start = event.start.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
        let end = event.end;
        
        // If no end time, set it to the end of the day
        if (!end) {
            end = new Date(event.start);
            end.setHours(23, 59, 59);
        }
        
        const endStr = end.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
        
        icsContent.push(
            'BEGIN:VEVENT',
            `UID:${event.id}@taskmanagement.app`,
            `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')}`,
            `DTSTART:${start}`,
            `DTEND:${endStr}`,
            `SUMMARY:${event.title}`,
            `DESCRIPTION:Status: ${event.extendedProps.status}\\nProject: ${event.extendedProps.project}\\nAssignee: ${event.extendedProps.assignee}`,
            'END:VEVENT'
        );
    });
    
    icsContent.push('END:VCALENDAR');
    
    // Create download link
    const blob = new Blob([icsContent.join('\n')], { type: 'text/calendar' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'task_calendar.ics';
    
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }, 100);
    
    showToast('Calendar exported successfully', 'success');
}
