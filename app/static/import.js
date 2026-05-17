document.getElementById("uploadForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];

    // Basic client-side validation
    if (!file) {
        alert("Please select a file to upload.");
        return;
    }

    if (!file.name.toLowerCase().endsWith(".ics")) {
        alert("Please upload a valid .ics file.");
        return;
    }

    file.text()
    .then(text => {
      if (!text.includes("BEGIN:VCALENDAR") || !text.includes("END:VCALENDAR")) {
        throw new Error("Invalid .ics file format.");
      }
      if (!text.includes("BEGIN:VEVENT")) {
        throw new Error("No events found in the .ics file.");
      }

      const formData = new FormData();
      formData.append("file", file);

      return fetch("/upload", {
          method: "POST",
          body: formData
      });
    })

    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to save event');
            });
        }
        
        alert('Successfully imported calendar!')
    })
    .catch(error => {
        alert('Error importing calendar: ' + error.message);
    });
});

// Handles uploading and importing .ics calendar files
document.getElementById("exportBtn").addEventListener("click", async () => {
  fetch("/export/ics", {
    method: "GET"
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(data => {
        throw new Error(data.error || "Export failed");
      });
    }

    return response.blob(); // important for file download
  })

  .then(blob => {
    if (!blob || blob.size === 0) {
      throw new Error("Export file is empty");
    }
    
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "calendar.ics";
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);
  })
  // Error message
  .catch(error => {
    alert("Error exporting calendar: " + error.message);
  });
});