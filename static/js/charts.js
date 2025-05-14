/**
 * Charts JavaScript for Task Management Application
 */

document.addEventListener('DOMContentLoaded', function() {
    initProjectStatusChart();
    initProjectProgressChart();
    initTaskPriorityChart();
    initTaskCompletionChart();
    initTeamWorkloadChart();
});

/**
 * Initialize project status distribution chart
 */
function initProjectStatusChart() {
    const chartElement = document.getElementById('project-status-chart');
    
    if (!chartElement) {
        return; // Exit if chart element doesn't exist
    }
    
    // Get data from the data attributes
    const labels = JSON.parse(chartElement.getAttribute('data-labels'));
    const data = JSON.parse(chartElement.getAttribute('data-values'));
    
    new Chart(chartElement, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#4c6ef5', // Primary - Planning
                    '#15aabf', // Info - In Progress
                    '#fd7e14', // Warning - On Hold
                    '#20c997', // Success - Completed
                    '#fa5252'  // Danger - Cancelled
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        boxWidth: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize project progress chart
 */
function initProjectProgressChart() {
    const chartElement = document.getElementById('project-progress-chart');
    
    if (!chartElement) {
        return; // Exit if chart element doesn't exist
    }
    
    // Get data from the data attributes
    const labels = JSON.parse(chartElement.getAttribute('data-labels'));
    const data = JSON.parse(chartElement.getAttribute('data-values'));
    
    new Chart(chartElement, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Completion Percentage',
                data: data,
                backgroundColor: '#4c6ef5',
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Progress: ${context.raw}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize task priority distribution chart
 */
function initTaskPriorityChart() {
    const chartElement = document.getElementById('task-priority-chart');
    
    if (!chartElement) {
        return; // Exit if chart element doesn't exist
    }
    
    // Get data from the data attributes
    const labels = JSON.parse(chartElement.getAttribute('data-labels'));
    const data = JSON.parse(chartElement.getAttribute('data-values'));
    
    new Chart(chartElement, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#15aabf', // Info - Low
                    '#fd7e14', // Warning - Medium
                    '#fd7e14', // Secondary - High
                    '#fa5252'  // Danger - Urgent
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        boxWidth: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize task completion trend chart
 */
function initTaskCompletionChart() {
    const chartElement = document.getElementById('task-completion-chart');
    
    if (!chartElement) {
        return; // Exit if chart element doesn't exist
    }
    
    // Get data from the data attributes
    const labels = JSON.parse(chartElement.getAttribute('data-labels'));
    const data = JSON.parse(chartElement.getAttribute('data-values'));
    
    new Chart(chartElement, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Completed Tasks',
                data: data,
                borderColor: '#20c997',
                backgroundColor: 'rgba(32, 201, 151, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return formatDate(context[0].label);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize team workload chart
 */
function initTeamWorkloadChart() {
    const chartElement = document.getElementById('team-workload-chart');
    
    if (!chartElement) {
        return; // Exit if chart element doesn't exist
    }
    
    // Get data from the data attributes
    const labels = JSON.parse(chartElement.getAttribute('data-labels'));
    const data = JSON.parse(chartElement.getAttribute('data-values'));
    
    new Chart(chartElement, {
        type: 'horizontalBar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Assigned Tasks',
                data: data,
                backgroundColor: '#4c6ef5',
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

/**
 * Initialize burndown chart
 * @param {string} elementId - ID of the chart element
 * @param {Array} idealBurndown - Ideal burndown data points
 * @param {Array} actualBurndown - Actual burndown data points
 * @param {Array} labels - Date labels
 */
function initBurndownChart(elementId, idealBurndown, actualBurndown, labels) {
    const chartElement = document.getElementById(elementId);
    
    if (!chartElement) {
        return; // Exit if chart element doesn't exist
    }
    
    new Chart(chartElement, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Ideal Burndown',
                    data: idealBurndown,
                    borderColor: '#adb5bd',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Actual Burndown',
                    data: actualBurndown,
                    borderColor: '#4c6ef5',
                    backgroundColor: 'rgba(76, 110, 245, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    title: {
                        display: true,
                        text: 'Remaining Tasks'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });
}

/**
 * Create a custom chart for specific data visualization
 * @param {string} elementId - ID of the chart element
 * @param {string} type - Chart type ('bar', 'line', 'pie', etc.)
 * @param {Array} labels - Chart labels
 * @param {Array} datasets - Chart datasets
 * @param {Object} options - Chart options
 */
function createCustomChart(elementId, type, labels, datasets, options = {}) {
    const chartElement = document.getElementById(elementId);
    
    if (!chartElement) {
        return; // Exit if chart element doesn't exist
    }
    
    new Chart(chartElement, {
        type: type,
        data: {
            labels: labels,
            datasets: datasets
        },
        options: Object.assign({
            responsive: true,
            maintainAspectRatio: false
        }, options)
    });
}
