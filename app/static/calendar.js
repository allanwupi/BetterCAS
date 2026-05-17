// Wrapper for server request to update event time and/or duration, given a JSON payload
async function updateEventInfo(isTask, payload, calendar, buttonToDisable) {
  // Backend route depending on whether it is a task or event
  const route = isTask ? '/save/task' : '/save/event';

let originalButtonText = "";

if (buttonToDisable) {
  buttonToDisable.disabled = true;
  originalButtonText = buttonToDisable.textContent;
  buttonToDisable.textContent = 'Saving...';
}

try {
  const response = await fetch(route, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || 'Failed to save event');
  }

  calendar.refetchEvents();
  return response;
} finally {
  if (buttonToDisable) {
    buttonToDisable.disabled = false;
    buttonToDisable.textContent = originalButtonText;
  }
}

  try {
    const response = await fetch(route, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || 'Failed to save event');
    }

    // Refresh calendar to ensure server values are shown
    calendar.refetchEvents();
    return response;
  } finally {
    if (buttonToDisable) {
      buttonToDisable.disabled = false;
      buttonToDisable.textContent = originalButtonText;
    }
  }
}

// Helper function to convert FullCalendar Event object into plain JSON
function eventToJson(event, isTask) {
  // Format dates as ISO strings in local time, not UTC
  function formatLocalISO(date) {
    if (!date) return null;

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
  }

  // Create payload object containing all important event information
  const payload = {
    id: event.id,
    title: event.title,
    start: event.start ? formatLocalISO(event.start) : null,
    end: isTask
      ? event.start
        ? formatLocalISO(event.start)
        : null
      : event.end
        ? formatLocalISO(event.end)
        : null,
    location:
      event.extendedProps && event.extendedProps.location
        ? event.extendedProps.location
        : '',
    description:
      event.extendedProps && event.extendedProps.description
        ? event.extendedProps.description
        : '',
    backgroundColor:
      event.backgroundColor ||
      (event.extendedProps && event.extendedProps.backgroundColor) ||
      '#6366f1',
    isTask: isTask,
    taskStatus: isTask ? event.extendedProps.taskStatus : undefined
  };

  return payload;
}

document.addEventListener('DOMContentLoaded', function () {
  // Read the CSRF token embedded in the HTML page.
   const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute('content');

  const CALENDAR_HEIGHT_RATIO = 0.9;

  const calendarEl = document.getElementById('calendar');
  const tooltip = document.getElementById('eventTooltip');

  const openEventModalBtn = document.getElementById('openEventModalBtn');
  const saveEventBtn = document.getElementById('saveEventBtn');

  const eventTitleInput = document.getElementById('eventTitle');
  const eventStartInput = document.getElementById('eventStart');
  const eventEndInput = document.getElementById('eventEnd');
  const eventLocationInput = document.getElementById('eventLocation');
  const eventDescriptionInput = document.getElementById('eventDescription');
  const eventIsTaskInput = document.getElementById('eventIsTask');

  const addEventModalElement = document.getElementById('addEventModal');
  const addEventModal = new bootstrap.Modal(addEventModalElement);

  const eventDetailsModalElement = document.getElementById('eventDetailsModal');
  const eventDetailsModal = new bootstrap.Modal(eventDetailsModalElement);

  const detailsTitle = document.getElementById('detailsTitle');
  const detailsStartLabel = document.getElementById('detailsStartLabel');
  const detailsStart = document.getElementById('detailsStart');
  const detailsEndRow = document.getElementById('detailsEndRow');
  const detailsEnd = document.getElementById('detailsEnd');
  const detailsStatusRow = document.getElementById('detailsStatusRow');
  const detailsStatus = document.getElementById('detailsStatus');
  const detailsLocationRow = document.getElementById('detailsLocationRow');
  const detailsLocation = document.getElementById('detailsLocation');
  const detailsDescriptionRow = document.getElementById('detailsDescriptionRow');
  const detailsDescription = document.getElementById('detailsDescription');
  const deleteEventBtn = document.getElementById('deleteEventBtn');

  let selectedEvent = null;

  // Helper function to display dates in a user-friendly format
  function formatDateTime(date) {
    if (!date) return 'N/A';

    return date.toLocaleString([], {
      dateStyle: 'medium',
      timeStyle: 'short'
    });
  }

  // Opens the details modal and fills it with event/task information
  function showEventDetails(event) {
    selectedEvent = event;

    const isTask = event.extendedProps.isTask;
    const start = formatDateTime(event.start);
    const end = event.end ? formatDateTime(event.end) : start;
    const location = event.extendedProps.location || 'No location provided';
    const description = event.extendedProps.description || 'No details provided';
    const taskStatus = event.extendedProps.taskStatus || 'No status provided';

    detailsTitle.textContent = event.title || 'Untitled';

    // Display different information depending on whether it is a task or event
    if (isTask) {
      detailsStartLabel.textContent = 'Due:';
      detailsStart.textContent = start;

      detailsEndRow.style.display = 'none';

      detailsStatusRow.style.display = 'block';
      detailsStatus.textContent = taskStatus;

      detailsLocationRow.style.display = 'none';
      detailsDescriptionRow.style.display = 'none';

      deleteEventBtn.textContent = 'Delete Task';
    } else {
      detailsStartLabel.textContent = 'Start:';
      detailsStart.textContent = start;

      detailsEndRow.style.display = 'block';
      detailsEnd.textContent = end;

      detailsStatusRow.style.display = 'none';

      detailsLocationRow.style.display = 'block';
      detailsLocation.textContent = location;

      detailsDescriptionRow.style.display = 'block';
      detailsDescription.textContent = description;

      deleteEventBtn.textContent = 'Delete Event';
    }

    tooltip.style.display = 'none';
    eventDetailsModal.show();
  }

  // Deletes the currently selected event/task
  async function deleteSelectedEvent(calendar) {
    if (!selectedEvent) {
      alert('No event selected.');
      return;
    }

    const isTask = selectedEvent.extendedProps.isTask;
    const itemType = isTask ? 'task' : 'event';

    // Confirmation Warning before deletion
    const confirmed = confirm(
      `Warning: this ${itemType} is going to be deleted. Are you sure you want to continue?`
    );

    if (!confirmed) {
      return;
    }

    deleteEventBtn.disabled = true;
    deleteEventBtn.textContent = isTask ? 'Deleting Task...' : 'Deleting Event...';

    try {
      const response = await fetch('/delete-event', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          id: selectedEvent.id
        })
      });

      const data = await response.json();
      
      //Handle backend errors
      if (!response.ok) {
        throw new Error(data.error || 'Failed to delete event');
      }

      selectedEvent.remove();
      selectedEvent = null;
      eventDetailsModal.hide();
      calendar.refetchEvents();
    } catch (error) {
      alert('Error deleting event: ' + error.message);
    } finally {
      deleteEventBtn.disabled = false;
      deleteEventBtn.textContent = isTask ? 'Delete Task' : 'Delete Event';
    }
  }

  const calendar = new FullCalendar.Calendar(calendarEl, {
    fixedWeekCount: false,
    initialView: 'dayGridMonth',
    height: window.innerHeight * CALENDAR_HEIGHT_RATIO,
    scrollTime: '08:00:00',
    allDaySlot: false,
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,timeGridDay'
    },
    selectable: true,
    editable: true,
    nowIndicator: true,
    events: '/get-events',

    // Allow user to drag, drop and resize events on the calendar, updating the database.
    eventChange: function (changeInfo) {
      const event = changeInfo.event;
      const isTask = event.extendedProps.isTask;
      const payload = eventToJson(event, isTask);

      updateEventInfo(isTask, payload, calendar).catch(error => {
        alert('Error saving event: ' + error.message);
        calendar.refetchEvents();
      });
    },

    eventClick: function (info) {
      info.jsEvent.preventDefault();
      showEventDetails(info.event);
    },

    // Triggered when mouse hovers over an event
    eventMouseEnter: function (info) {
      const event = info.event;
      const start = event.start
        ? event.start.toLocaleString([], {
            dateStyle: 'medium',
            timeStyle: 'short'
          })
        : 'N/A';

      const end = event.end
        ? event.end.toLocaleString([], {
            dateStyle: 'medium',
            timeStyle: 'short'
          })
        : start;

      const location = event.extendedProps.location || 'No location provided';
      const description =
        event.extendedProps.description || 'No description provided';

      if (event.extendedProps.isTask) {
        //Tooltip layout for tasks
        tooltip.innerHTML = `
          <strong>${event.title}</strong>
          <div><span class="tooltip-label">Due:</span> ${end}</div> 
          <div><span class="tooltip-label">Status:</span> ${event.extendedProps.taskStatus}</div>
        `;
      } else {
        //Tooltip layout for events
        tooltip.innerHTML = `
          <strong>${event.title}</strong>
          <div><span class="tooltip-label">Start:</span> ${start}</div>
          <div><span class="tooltip-label">End:</span> ${end}</div>
          <div><span class="tooltip-label">Location:</span> ${location}</div>
          <div><span class="tooltip-label">Details:</span> ${description}</div>
        `;
      }

      tooltip.style.display = 'block';
    },

    eventMouseLeave: function () {
      tooltip.style.display = 'none';
    }
  });

  calendar.render();

  calendarEl.addEventListener('mousemove', function (e) {
    tooltip.style.left = e.pageX + 16 + 'px';
    tooltip.style.top = e.pageY + 16 + 'px';
  });

  window.addEventListener('resize', function () {
    calendar.setOption('height', window.innerHeight * CALENDAR_HEIGHT_RATIO);
  });

  openEventModalBtn.addEventListener('click', () => {
    eventTitleInput.value = '';
    eventStartInput.value = '';
    eventEndInput.value = '';
    eventLocationInput.value = '';
    eventDescriptionInput.value = '';
    eventIsTaskInput.checked = false;

    addEventModal.show();
  });

  // Automatically fill in event end times upon receiving start time input
  eventStartInput.addEventListener('input', () => {
    if (!eventEndInput.value || eventEndInput.value < eventStartInput.value) {
      eventEndInput.value = eventStartInput.value;
    }
  });

  saveEventBtn.addEventListener('click', async () => {
    // Get values from form
    const title = eventTitleInput.value.trim();
    const start = eventStartInput.value;
    const end = eventEndInput.value;
    const location = eventLocationInput.value.trim();
    const description = eventDescriptionInput.value.trim();
    const isTask = eventIsTaskInput.checked;

    // Client-side validation
    if (!title || !start || !end) {
      alert('Please enter the event title, start and end dates/times.');
      return;
    }

    if (!isTask && end <= start) {
      alert('End date/time must be after the start date/time.');
      return;
    }

    const payload = {
      title: title,
      start: start,
      end: end,
      location: location,
      description: description,
      backgroundColor: '#6366f1',
      isTask: isTask,
      
      // Default task status
      taskStatus: isTask ? 'Not Started' : undefined
    };

    try {
      await updateEventInfo(isTask, payload, calendar, saveEventBtn);
      addEventModal.hide();
    } catch (error) {
      alert('Error saving event: ' + error.message);
    }
  });

  deleteEventBtn.addEventListener('click', () => {
    deleteSelectedEvent(calendar);
  });
});