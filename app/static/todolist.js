document.addEventListener('DOMContentLoaded', function () {
  const todoInput = document.getElementById('todoInput');
  const todoDate = document.getElementById('todoDate');
  const addTodoBtn = document.getElementById('addTodoBtn');
  const todoList = document.getElementById('todoList');
  const filterButtons = document.querySelectorAll('.filter-buttons button');

  // Tracks which filter is currently active: all, pending, or completed
  let currentFilter = 'all';

  // Formats the task due date into a readable date/time
  function formatDate(dateString) {
    if (!dateString) return 'No due date';
    const date = new Date(dateString);
    const datePart = date.toLocaleDateString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
    const timePart = date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
    return `${datePart} ${timePart}`;
  }

  // For the Bootstrap badge colour based on task status
  function getBadgeClass(status) {
    if (status === 'Not Started') return 'bg-info text-dark';
    if (status === 'In Progress') return 'bg-warning text-dark';
    if (status === 'Completed') return 'bg-success';
    return 'bg-secondary';
  }

  function getTaskItems() {
    return Array.from(todoList.querySelectorAll('.task-item'));
  }

  // Shows "No tasks found" when the filtered list is empty
  function setEmptyState() {
    const taskItems = getTaskItems();
    const visibleTaskItems = taskItems.filter(taskItem => !taskItem.classList.contains('d-none'));
    const emptyState = todoList.querySelector('.empty-state');

    if (visibleTaskItems.length === 0) {
      if (!emptyState) {
        const emptyItem = document.createElement('li');
        emptyItem.className = 'empty-state';
        emptyItem.textContent = 'No tasks found.';
        todoList.appendChild(emptyItem);
      }
      return;
    }

    if (emptyState && taskItems.length > 0) {
      emptyState.remove();
    }
  }

  function wireDropdown(dropdown) {
    dropdown.addEventListener('show.bs.dropdown', () => {
      dropdown.closest('.task-item')?.classList.add('dropdown-open');
    });

    dropdown.addEventListener('hide.bs.dropdown', () => {
      dropdown.closest('.task-item')?.classList.remove('dropdown-open');
    });
  }

  // Creates a new task list item using task data from the server
  function createTaskItem(task) {
    const li = document.createElement('li');
    li.className = 'task-item d-flex justify-content-between align-items-center';
    li.dataset.taskId = task.id;
    li.dataset.status = task.status;
    li.dataset.dueDate = task.dueDate || '';
    li.dataset.title = task.title;

    li.innerHTML = `
        <div class="task-left">
          <p class="fw-bold ${task.status === 'Completed' ? 'text-decoration-line-through text-muted' : ''}">
            ${task.title}
          </p>
          <small>Due: ${formatDate(task.dueDate)}</small>
        </div>

        <div class="d-flex gap-2 align-items-center flex-wrap justify-content-end">
          <div class="dropdown">
            <button class="btn btn-sm btn-outline-secondary dropdown-toggle rounded-pill px-3" data-bs-toggle="dropdown">
              Status
            </button>
            <ul class="dropdown-menu shadow border-0 rounded-4 p-2">
              <li><a class="dropdown-item rounded-3 status-option" href="#" data-id="${task.id}" data-status="Not Started"><span class="badge bg-info text-dark">Not Started</span></a></li>
              <li><a class="dropdown-item rounded-3 status-option" href="#" data-id="${task.id}" data-status="In Progress"><span class="badge bg-warning text-dark">In Progress</span></a></li>
              <li><a class="dropdown-item rounded-3 status-option" href="#" data-id="${task.id}" data-status="Completed"><span class="badge bg-success">Completed</span></a></li>
            </ul>
          </div>

          <span class="task-status-badge ${getBadgeClass(task.status)}">${task.status}</span>
          <button class="btn btn-danger btn-sm rounded-pill px-3 delete-task" data-id="${task.id}">Delete</button>
        </div>
      `;

    wireDropdown(li.querySelector('.dropdown'));
    return li;
  }

  // Applies the selected filter to show/hide tasks
  function applyFilter() {
    const taskItems = getTaskItems();

    taskItems.forEach(taskItem => {
      const status = taskItem.dataset.status;
      let visible = true;

      if (currentFilter === 'pending') {
        visible = status !== 'Completed';
      } else if (currentFilter === 'completed') {
        visible = status === 'Completed';
      }

      if (visible) {
        taskItem.classList.remove('d-none');
      } else {
        taskItem.classList.add('d-none');
      }
    });

    setEmptyState();
  }

  addTodoBtn.addEventListener('click', () => {
    const title = todoInput.value.trim();
    const dueDate = todoDate.value;

    if (title === '') {
      alert('Please enter a task.');
      return;
    }

    if (!dueDate) {
      alert('Please set a due date.');
      return;
    }

    const emptyState = todoList.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }

    // Disable the button while saving
    addTodoBtn.disabled = true;
    // Save the new task to the backend
    fetch('/save/task', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        title: title,
        start: dueDate,
        end: dueDate,
        backgroundColor: '#6366f1',
        isTask: true,
        taskStatus: 'Not Started'
      })
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(data => {
          throw new Error(data.error || 'Failed to save task');
        });
      }
      return response.json();
    })
    .then(savedTask => {
      // Create task item with the saved data (includes server-generated ID)
      const taskItem = createTaskItem({
        id: savedTask.id,
        title: savedTask.title,
        dueDate: savedTask.end,
        status: savedTask.extendedProps.taskStatus
      });
      todoList.appendChild(taskItem);
      todoInput.value = '';
      todoDate.value = '';
      applyFilter();
    })
    .catch(error => {
      alert('Error adding task: ' + error.message);
    })
    .finally(() => {
      addTodoBtn.disabled = false;
    });
  });

  // Handles delete and status button clicks inside the todo list
  todoList.addEventListener('click', (e) => {
    if (e.target.closest('.delete-task')) {
      const button = e.target.closest('.delete-task');
      const taskItem = button.closest('.task-item');
      if (taskItem) {
        const taskId = taskItem.dataset.taskId;
        
        // Disable the button while deleting
        button.disabled = true;
        // Delete the selected task from the backend
        fetch('/delete-event', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ id: taskId })
        })
        .then(response => {
          if (!response.ok) {
            return response.json().then(data => {
              throw new Error(data.error || 'Failed to delete event');
            });
          }
          taskItem.remove();
          applyFilter();
        })
        .catch(error => {
          alert('Error deleting task: ' + error.message);
          button.disabled = false;
        });
      }
    }

    if (e.target.closest('.status-option')) {
      e.preventDefault();
      const option = e.target.closest('.status-option');
      const taskItem = option.closest('.task-item');
      const newStatus = option.dataset.status;

      if (taskItem) {
        const taskId = taskItem.dataset.taskId;
        const statusButton = taskItem.querySelector('.dropdown-toggle');
        // Update the selected task's status in the backend
        fetch('/update-task-status', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ id: taskId, status: newStatus })
        })
        .then(response => {
          if (!response.ok) {
            return response.json().then(data => {
              throw new Error(data.error || 'Failed to update task status');
            });
          }
          // Update the task item with the new status
          taskItem.dataset.status = newStatus;

          const titleElement = taskItem.querySelector('.task-left p');
          const statusBadge = taskItem.querySelector('.task-status-badge');

          if (titleElement) {
            titleElement.classList.toggle('text-decoration-line-through', newStatus === 'Completed');
            titleElement.classList.toggle('text-muted', newStatus === 'Completed');
          }

          if (statusBadge) {
            statusBadge.className = `task-status-badge ${getBadgeClass(newStatus)}`;
            statusBadge.textContent = newStatus;
          }

          applyFilter();
        })
        .catch(error => {
          alert('Error updating task status: ' + error.message);
        });
      }
    }
  });

  // Set up filter buttons for all, pending, and completed tasks
  filterButtons.forEach(button => {
    button.addEventListener('click', () => {
      filterButtons.forEach(btn => btn.classList.remove('active-filter'));
      button.classList.add('active-filter');
      currentFilter = button.dataset.filter;
      applyFilter();
    });
  });

  todoList.querySelectorAll('.dropdown').forEach(wireDropdown);
  applyFilter();
});