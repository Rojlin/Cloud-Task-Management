/**
 * Kanban Board JavaScript for Task Management Application
 */

document.addEventListener('DOMContentLoaded', function() {
    initKanbanBoard();
});

/**
 * Initialize the Kanban board with drag-and-drop functionality
 */
function initKanbanBoard() {
    // Get all columns
    const columns = document.querySelectorAll('.kanban-column-content');
    
    if (columns.length === 0) {
        return; // Exit if no kanban board present
    }
    
    // Initialize Sortable for each column
    columns.forEach(column => {
        new Sortable(column, {
            group: 'tasks', // Set group name for shared lists
            animation: 150,
            ghostClass: 'kanban-card-ghost',
            chosenClass: 'kanban-card-chosen',
            dragClass: 'kanban-card-drag',
            
            onEnd: function(evt) {
                // Get task ID and new status
                const taskId = evt.item.getAttribute('data-task-id');
                const newStatus = evt.to.getAttribute('data-status');
                
                if (taskId && newStatus) {
                    updateTaskStatus(taskId, newStatus);
                }
            }
        });
    });
    
    // Initialize Add Task buttons
    const addTaskButtons = document.querySelectorAll('.kanban-add-card');
    
    addTaskButtons.forEach(button => {
        button.addEventListener('click', function() {
            const projectId = this.getAttribute('data-project-id');
            const status = this.getAttribute('data-status');
            
            // Redirect to create task page with pre-filled status
            let url = '/tasks/create/';
            
            if (projectId) {
                url += `?project=${projectId}&status=${status}`;
            } else {
                url += `?status=${status}`;
            }
            
            window.location.href = url;
        });
    });
}

/**
 * Update the task status via API
 * @param {string} taskId - The ID of the task to update
 * @param {string} newStatus - The new status value
 */
function updateTaskStatus(taskId, newStatus) {
    // Show progress indicator
    showToast('Updating task status...', 'info');
    
    // Send update via fetch API
    fetch('/tasks/api/update-position/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            taskId: taskId,
            newStatus: newStatus
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Update task status badge if present
            const statusBadges = document.querySelectorAll(`.task-status-badge-${taskId}`);
            if (statusBadges.length > 0) {
                statusBadges.forEach(badge => {
                    badge.textContent = data.newStatus;
                    
                    // Update badge classes
                    badge.className = 'badge';
                    
                    switch (newStatus) {
                        case 'todo':
                            badge.classList.add('badge-secondary');
                            break;
                        case 'in_progress':
                            badge.classList.add('badge-primary');
                            break;
                        case 'review':
                            badge.classList.add('badge-warning');
                            break;
                        case 'completed':
                            badge.classList.add('badge-success');
                            break;
                    }
                });
            }
            
            // Update counter
            updateColumnCounters();
            
            showToast('Task status updated successfully', 'success');
        } else {
            showToast('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error updating task status:', error);
        showToast('Failed to update task status. Please try again.', 'error');
        
        // Reload the page to reset the board
        setTimeout(() => {
            window.location.reload();
        }, 2000);
    });
}

/**
 * Update the task count in each column
 */
function updateColumnCounters() {
    const columns = document.querySelectorAll('.kanban-column');
    
    columns.forEach(column => {
        const counter = column.querySelector('.kanban-column-count');
        const cards = column.querySelectorAll('.kanban-card').length;
        
        if (counter) {
            counter.textContent = cards;
        }
    });
}

/**
 * Filter tasks on the Kanban board
 * @param {string} query - Search query string
 */
function filterKanbanTasks(query) {
    if (!query) {
        // Remove any existing filters
        document.querySelectorAll('.kanban-card').forEach(card => {
            card.style.display = '';
        });
        return;
    }
    
    query = query.toLowerCase();
    
    // Filter cards
    document.querySelectorAll('.kanban-card').forEach(card => {
        const title = card.querySelector('.kanban-card-title').textContent.toLowerCase();
        const assignee = card.getAttribute('data-assignee')?.toLowerCase() || '';
        const priority = card.getAttribute('data-priority')?.toLowerCase() || '';
        
        if (title.includes(query) || assignee.includes(query) || priority.includes(query)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * Toggle priority filter for Kanban tasks
 * @param {string} priority - Priority value to filter by
 */
function togglePriorityFilter(priority) {
    const filterButton = document.querySelector(`[data-priority-filter="${priority}"]`);
    const isActive = filterButton.classList.contains('active');
    
    // Clear other filters if holding Ctrl key
    if (!event.ctrlKey) {
        document.querySelectorAll('[data-priority-filter]').forEach(btn => {
            btn.classList.remove('active');
        });
        
        document.querySelectorAll('.kanban-card').forEach(card => {
            card.style.display = '';
        });
    }
    
    if (!isActive) {
        filterButton.classList.add('active');
        
        // Apply filter
        document.querySelectorAll('.kanban-card').forEach(card => {
            const cardPriority = card.getAttribute('data-priority');
            
            if (cardPriority !== priority) {
                card.style.display = 'none';
            } else {
                card.style.display = '';
            }
        });
    }
}

/**
 * Add a quick task directly to the Kanban board (without full form)
 * @param {string} status - The status column to add to
 * @param {string} projectId - The project ID
 */
function quickAddTask(status, projectId) {
    // Create a modal for quick task creation
    const modal = document.createElement('div');
    modal.classList.add('modal');
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Quick Add Task</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <form id="quick-task-form">
                        <div class="form-group">
                            <label for="task-title">Task Title</label>
                            <input type="text" class="form-control" id="task-title" required>
                        </div>
                        <div class="form-group">
                            <label for="task-priority">Priority</label>
                            <select class="form-control" id="task-priority">
                                <option value="low">Low</option>
                                <option value="medium" selected>Medium</option>
                                <option value="high">High</option>
                                <option value="urgent">Urgent</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="task-due-date">Due Date</label>
                            <input type="date" class="form-control" id="task-due-date" required>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="save-quick-task">Save Task</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Set default due date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    document.getElementById('task-due-date').value = tomorrow.toISOString().split('T')[0];
    
    // Handle close button
    modal.querySelector('[data-dismiss="modal"]').addEventListener('click', function() {
        document.body.removeChild(modal);
    });
    
    // Handle save button
    document.getElementById('save-quick-task').addEventListener('click', function() {
        const title = document.getElementById('task-title').value;
        const priority = document.getElementById('task-priority').value;
        const dueDate = document.getElementById('task-due-date').value;
        
        if (!title || !dueDate) {
            return; // Form validation failed
        }
        
        const formData = new FormData();
        formData.append('title', title);
        formData.append('priority', priority);
        formData.append('due_date', dueDate);
        formData.append('status', status);
        formData.append('project', projectId);
        
        // Submit via AJAX
        fetch('/tasks/create/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Add new task to the board
                const column = document.querySelector(`[data-status="${status}"]`);
                
                const taskCard = document.createElement('div');
                taskCard.classList.add('kanban-card', `priority-${priority}`);
                taskCard.setAttribute('data-task-id', data.task_id);
                taskCard.setAttribute('data-priority', priority);
                
                taskCard.innerHTML = `
                    <div class="kanban-card-header">
                        <h5 class="kanban-card-title">${title}</h5>
                        <span class="kanban-card-priority badge badge-${getPriorityBadgeClass(priority)}">${priority}</span>
                    </div>
                    <div class="kanban-card-meta">
                        <div class="kanban-card-date">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                                <line x1="16" y1="2" x2="16" y2="6"></line>
                                <line x1="8" y1="2" x2="8" y2="6"></line>
                                <line x1="3" y1="10" x2="21" y2="10"></line>
                            </svg>
                            ${formatDate(dueDate)}
                        </div>
                    </div>
                `;
                
                column.prepend(taskCard);
                updateColumnCounters();
                document.body.removeChild(modal);
                
                showToast('Task created successfully', 'success');
            } else {
                showToast('Error: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error creating task:', error);
            showToast('Failed to create task. Please try again.', 'error');
        });
    });
    
    // Show modal
    setTimeout(() => {
        modal.classList.add('show');
        document.getElementById('task-title').focus();
    }, 10);
}

/**
 * Get CSS class for priority badge
 * @param {string} priority - Priority value
 * @returns {string} CSS class for badge
 */
function getPriorityBadgeClass(priority) {
    switch (priority) {
        case 'low':
            return 'info';
        case 'medium':
            return 'warning';
        case 'high':
            return 'secondary';
        case 'urgent':
            return 'danger';
        default:
            return 'secondary';
    }
}
