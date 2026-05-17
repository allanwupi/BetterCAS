// Stores the friends, availability comparison items and requests loaded from the backend
let friends = [];
let pendingSent = [];
let pendingReceived = [];
let selectedFriends = [];
let availabilityCalendar = null;
let searchDebounceTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  setupFriendSearch();
  setupAvailabilityCalendar();
  loadFriendsData();

  document
    .getElementById("compareFriendsBtn")
    .addEventListener("click", handleCompareAvailabilityClick);
});

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  let data = null;

  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  if (!response.ok) {
    const message = data && data.error
      ? data.error
      : "Something went wrong. Please try again.";
    throw new Error(message);
  }

  return data;
}

function setStatusMessage(message) {
  const statusMessage = document.getElementById("friendsStatusMessage");

  if (statusMessage) {
    statusMessage.textContent = message;
  }
}

function getDisplayName(user) {
  if (!user) return "Unknown user";

  if (user.username) {
    return `@${user.username}`;
  }

  return user.email;
}

function setupFriendSearch() {
  const input = document.getElementById("friendSearchInput");

  input.addEventListener("input", () => {
    clearTimeout(searchDebounceTimer);

    //Helps with avoiding too many API calls
    searchDebounceTimer = setTimeout(() => {
      searchUsers(input.value.trim());
    }, 300);
  });
}

async function searchUsers(query) {
  const results = document.getElementById("friendSearchResults");
  results.innerHTML = "";

  if (!query) {
    results.innerHTML = `<p class="friends-muted">Type a username or email to search.</p>`;
    return;
  }

  results.innerHTML = `<p class="friends-muted">Searching...</p>`;

  try {
    const users = await apiRequest(`/api/friends/search?query=${encodeURIComponent(query)}`);
    renderSearchResults(users);
  } catch (error) {
    results.innerHTML = `<p class="friends-muted">${error.message}</p>`;
  }
}

function renderSearchResults(users) {
  const results = document.getElementById("friendSearchResults");
  results.innerHTML = "";

  if (!users || users.length === 0) {
    results.innerHTML = `<p class="friends-muted">No users found.</p>`;
    return;
  }

  users.forEach(user => {
    const row = document.createElement("div");
    row.className = "friend-row";

    const label = document.createElement("span");
    label.textContent = `${getDisplayName(user)} (${user.email})`;

    const button = document.createElement("button");
    button.className = "friends-small-btn";

    if (user.friendship_status === "accepted") {
      button.textContent = "Already Friends";
      button.disabled = true;
    } else if (user.friendship_status === "pending") {
      button.textContent = "Pending";
      button.disabled = true;
    } else if (user.friendship_status === "rejected") {
      button.textContent = "Rejected";
      button.disabled = true;
    } else {
      button.textContent = "Add Friend";
      button.addEventListener("click", () => sendFriendRequest(user.email));
    }

    row.appendChild(label);
    row.appendChild(button);
    results.appendChild(row);
  });
}

// Sends a friend request to the selected user
async function sendFriendRequest(receiverEmail) {
  try {
    await apiRequest("/api/friends/send-request", {
      method: "POST",
      body: JSON.stringify({ receiver_email: receiverEmail })
    });

    document.getElementById("friendSearchInput").value = "";
    document.getElementById("friendSearchResults").innerHTML = "";
    setStatusMessage("Friend request sent successfully.");
    await loadFriendsData();
  } catch (error) {
    setStatusMessage(error.message);
  }
}

// Loads accepted friends, sent requests, and received requests from backend
async function loadFriendsData() {
  try {
    const data = await apiRequest("/api/friends/list");

    friends = data.friends || [];
    pendingSent = data.pending_sent || [];
    pendingReceived = data.pending_received || [];

    selectedFriends = selectedFriends.filter(selected =>
      friends.some(friend => friend.email === selected.email)
    );

    renderFriends();
    renderPendingSent();
    renderPendingReceived();
    renderSelectedFriends();
  } catch (error) {
    setStatusMessage(error.message);
  }
}

// Gives the user options to select or remove their accepted friends
function renderFriends() {
  const list = document.getElementById("friendsList");
  list.innerHTML = "";

  if (friends.length === 0) {
    list.innerHTML = `<p class="friends-muted">No friends yet. Search for users and send requests.</p>`;
    return;
  }

  friends.forEach(friend => {
    const row = document.createElement("div");
    row.className = "friend-row";

    const label = document.createElement("span");
    label.textContent = `${getDisplayName(friend)} (${friend.email})`;

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";

    const selectButton = document.createElement("button");
    selectButton.className = "friends-small-btn";
    selectButton.textContent = isSelected(friend.email) ? "Selected" : "Select";
    selectButton.disabled = isSelected(friend.email);
    selectButton.addEventListener("click", () => selectFriend(friend));

    const removeButton = document.createElement("button");
    removeButton.className = "friends-remove-btn";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => removeFriend(friend.friendship_id));

    actions.appendChild(selectButton);
    actions.appendChild(removeButton);

    row.appendChild(label);
    row.appendChild(actions);
    list.appendChild(row);
  });
}

function renderPendingSent() {
  const list = document.getElementById("outgoingRequestsList");
  list.innerHTML = "";

  if (pendingSent.length === 0) {
    list.innerHTML = `<p class="friends-muted">No outgoing requests.</p>`;
    return;
  }

  pendingSent.forEach(request => {
    const row = document.createElement("div");
    row.className = "friend-row";

    const label = document.createElement("span");
    label.textContent = `${getDisplayName(request)} (${request.email})`;

    const cancelButton = document.createElement("button");
    cancelButton.className = "friends-remove-btn";
    cancelButton.textContent = "Cancel";
    cancelButton.addEventListener("click", () => removeFriend(request.friendship_id));

    row.appendChild(label);
    row.appendChild(cancelButton);
    list.appendChild(row);
  });
}

function renderPendingReceived() {
  const list = document.getElementById("incomingRequestsList");
  list.innerHTML = "";

  if (pendingReceived.length === 0) {
    list.innerHTML = `<p class="friends-muted">No incoming requests.</p>`;
    return;
  }

  pendingReceived.forEach(request => {
    const row = document.createElement("div");
    row.className = "friend-row";

    const label = document.createElement("span");
    label.textContent = `${getDisplayName(request)} (${request.email})`;

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";

    const acceptButton = document.createElement("button");
    acceptButton.className = "friends-small-btn";
    acceptButton.textContent = "Accept";
    acceptButton.addEventListener("click", () => acceptRequest(request.friendship_id));

    const rejectButton = document.createElement("button");
    rejectButton.className = "friends-remove-btn";
    rejectButton.textContent = "Reject";
    rejectButton.addEventListener("click", () => rejectRequest(request.friendship_id));

    actions.appendChild(acceptButton);
    actions.appendChild(rejectButton);

    row.appendChild(label);
    row.appendChild(actions);
    list.appendChild(row);
  });
}

// Accepts an incoming friend request
async function acceptRequest(friendshipId) {
  try {
    await apiRequest(`/api/friends/accept-request/${friendshipId}`, {
      method: "POST"
    });

    setStatusMessage("Friend request accepted.");
    await loadFriendsData();
  } catch (error) {
    setStatusMessage(error.message);
  }
}

async function rejectRequest(friendshipId) {
  try {
    await apiRequest(`/api/friends/reject-request/${friendshipId}`, {
      method: "POST"
    });

    setStatusMessage("Friend request rejected.");
    await loadFriendsData();
  } catch (error) {
    setStatusMessage(error.message);
  }
}

// Removes either an existing friend or pending friend request
async function removeFriend(friendshipId) {
  const confirmed = confirm("Are you sure you want to remove this friend or request?");

  if (!confirmed) return;

  try {
    await apiRequest(`/api/friends/remove/${friendshipId}`, {
      method: "DELETE"
    });

    setStatusMessage("Friend or request removed.");
    await loadFriendsData();
  } catch (error) {
    setStatusMessage(error.message);
  }
}

// Adds a friend to the availability comparison list
function selectFriend(friend) {
  if (isSelected(friend.email)) return;

  // Limits comparison to a maximum of 3 selected friends
  if (selectedFriends.length >= 3) {
    alert("You can only select up to 3 friends.");
    return;
  }

  selectedFriends.push(friend);
  renderFriends();
  renderSelectedFriends();
}

function isSelected(email) {
  return selectedFriends.some(friend => friend.email === email);
}

function renderSelectedFriends() {
  const list = document.getElementById("selectedFriendsList");
  list.innerHTML = "";

  if (selectedFriends.length === 0) {
    list.innerHTML = `<p class="friends-muted">No friends selected yet.</p>`;
    return;
  }

  selectedFriends.forEach(friend => {
    const row = document.createElement("div");
    row.className = "friend-row selected";

    const label = document.createElement("span");
    label.textContent = `${getDisplayName(friend)} (${friend.email})`;

    const removeButton = document.createElement("button");
    removeButton.className = "friends-remove-btn";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => {
      selectedFriends = selectedFriends.filter(item => item.email !== friend.email);
      renderFriends();
      renderSelectedFriends();
      clearAvailabilityCalendar();
    });

    row.appendChild(label);
    row.appendChild(removeButton);
    list.appendChild(row);
  });
}

function setupAvailabilityCalendar() {
  const calendarElement = document.getElementById("friendsAvailabilityCalendar");

  availabilityCalendar = new FullCalendar.Calendar(calendarElement, {
    initialView: "timeGridWeek",
    allDaySlot: false,
    slotMinTime: "08:00:00",
    slotMaxTime: "20:00:00",
    height: "auto",
    nowIndicator: true,
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "timeGridWeek"
    },
    eventDidMount: info => {
      if (info.event.display === "background") return;

      const props = info.event.extendedProps || {};
      const ownerLabel = props.is_current_user_event
        ? "You"
        : `@${props.owner_username}`;

      info.el.title = `${info.event.title} (${ownerLabel})`;
    },
    events: []
  });

  availabilityCalendar.render();
}

function clearAvailabilityCalendar() {
  if (availabilityCalendar) {
    availabilityCalendar.removeAllEvents();
  }
}

async function handleCompareAvailabilityClick() {
  if (selectedFriends.length === 0) {
    alert("Select at least one friend first.");
    return;
  }

  await loadAvailabilityComparison();
}

// Loads shared availability data for the selected friends and current week (compare button must be refreshed for showing other weeks)
async function loadAvailabilityComparison() {
  if (!availabilityCalendar) return;

  const selectedNames = selectedFriends.map(friend => getDisplayName(friend)).join(", ");
  const activeRange = availabilityCalendar.view.activeStart && availabilityCalendar.view.activeEnd
    ? {
        start: availabilityCalendar.view.activeStart.toISOString(),
        end: availabilityCalendar.view.activeEnd.toISOString()
      }
    : null;

  if (!activeRange) {
    setStatusMessage("Calendar range could not be loaded.");
    return;
  }

  setStatusMessage(`Comparing availability with ${selectedNames}...`);

  try {
    const data = await apiRequest("/api/friends/availability", {
      method: "POST",
      body: JSON.stringify({
        friend_emails: selectedFriends.map(friend => friend.email),
        start: activeRange.start,
        end: activeRange.end
      })
    });

    availabilityCalendar.removeAllEvents();

    // Displays both free slots and busy events on the availability calendar
    const eventsToDisplay = [
      ...(data.free_slots || []),
      ...(data.busy_events || [])
    ];

    eventsToDisplay.forEach(event => availabilityCalendar.addEvent(event));

    setStatusMessage(
      `Showing availability with ${selectedNames}. Green means everyone is free. Red means someone is busy. Orange means you are unavailable`
    );
  } catch (error) {
    setStatusMessage(error.message);
  }
}