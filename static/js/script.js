document.getElementById('submitButton').addEventListener('click', async () => {
    // Get values from form inputs
    const millId = document.getElementById('millDropdown').value;
    const machineId = document.getElementById('machineDropdown').value;
    const date = document.getElementById('date').value;
    const saveDir = document.getElementById('saveDir').value;
    const defectType = document.getElementById('defectType').value;

    // Validate form inputs
    if (!millId || !machineId || !date || !saveDir || !defectType) {
        alert('Please fill all fields before submitting.');
        return;
    }

    // Prepare data to send to the backend
    const data = { millId, machineId, date, saveDir, defectType };

    try {
        // Send the data to the backend (Flask app)
        const response = await fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        // Handle the response from the backend
        const result = await response.json();
        const responseDiv = document.getElementById('response');
        responseDiv.innerHTML = ''; // Clear previous response

        if (response.ok) {
            // Display success message
            responseDiv.innerText = `Success: ${result.message}`;
            
            if (result.file) {
                // Provide a download link for the result file
                const downloadLink = document.createElement('a');
                downloadLink.href = result.file;
                downloadLink.textContent = 'Download the result file';
                downloadLink.target = '_blank';  // Open in new tab
                responseDiv.appendChild(document.createElement('br'));
                responseDiv.appendChild(downloadLink);
            }
        } else {
            // Display error message
            responseDiv.innerText = `Error: ${result.message}`;
        }
    } catch (error) {
        // Handle network or other errors
        const responseDiv = document.getElementById('response');
        responseDiv.innerText = `Error: ${error.message}`;
    }
});

// Fetch mills and populate the mill dropdown
async function fetchMills() {
    try {
        const response = await fetch('/get_mills');
        const data = await response.json();
        const millDropdown = document.getElementById('millDropdown');
        millDropdown.innerHTML = '<option value="">--Select a Mill--</option>';  // Clear existing options

        data.mills.forEach(mill => {
            const option = document.createElement('option');
            option.value = mill.milldetails_id;
            option.textContent = mill.mill_name;
            millDropdown.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching mills:', error);
        alert('Failed to load mills. Please try again later.');
    }
}

// Fetch machines based on the selected mill
async function fetchMachines() {
    const millDropdown = document.getElementById('millDropdown');
    const machineDropdown = document.getElementById('machineDropdown');
    const millId = millDropdown.value;

    // Clear existing options in the machine dropdown
    machineDropdown.innerHTML = '<option value="">--Select a Machine--</option>';

    if (millId) {
        try {
            const response = await fetch(`/get_machines/${millId}`);
            const data = await response.json();
            if (data.machines && data.machines.length > 0) {
                data.machines.forEach(machine => {
                    const option = document.createElement('option');
                    option.value = machine.machinedetail_id;
                    option.textContent = machine.machine_name;
                    machineDropdown.appendChild(option);
                });
            } else {
                machineDropdown.innerHTML = '<option value="">No machines available</option>';
            }
        } catch (error) {
            console.error('Error fetching machines:', error);
            alert('Failed to load machines. Please try again later.');
        }
    }
}

// Initialize mills on page load
document.addEventListener('DOMContentLoaded', fetchMills);

// Trigger fetch machines when a mill is selected
document.getElementById('millDropdown').addEventListener('change', fetchMachines);
