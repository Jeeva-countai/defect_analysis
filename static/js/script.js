document.addEventListener('DOMContentLoaded', () => {
    fetchMills();
    document.getElementById('millDropdown').addEventListener('change', fetchMachines);
    document.getElementById('submitButton').addEventListener('click', handleSubmit);
});

async function fetchMills() {
    const responseDiv = document.getElementById('response');
    responseDiv.innerHTML = ''; // Clear previous response

    try {
        const response = await fetch('/get_mills');
        const data = await response.json();
        const millDropdown = document.getElementById('millDropdown');
        millDropdown.innerHTML = '<option value="">--Select a Mill--</option>'; // Clear existing options

        if (data.mills && data.mills.length > 0) {
            data.mills.forEach(mill => {
                const option = document.createElement('option');
                option.value = mill.milldetails_id;
                option.textContent = mill.mill_name;
                millDropdown.appendChild(option);
            });
        } else {
            alert('No mills available.');
        }
    } catch (error) {
        console.error('Error fetching mills:', error);
        alert('Failed to load mills. Please try again later.');
    }
}

async function fetchMachines() {
    const millDropdown = document.getElementById('millDropdown');
    const machineDropdown = document.getElementById('machineDropdown');
    const millId = millDropdown.value;

    machineDropdown.innerHTML = '<option value="">--Select a Machine--</option>'; // Clear existing options

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

async function handleSubmit() {
    const millDropdown = document.getElementById('millDropdown');
    const machineDropdown = document.getElementById('machineDropdown');
    const date = document.getElementById('date').value;
    const saveDir = document.getElementById('saveDir').value;
    const defectType = document.getElementById('defectType').value;

    if (!millDropdown.value || !machineDropdown.value || !date || !saveDir || !defectType) {
        alert('Please fill all fields!');
        return;
    }

    const millName = millDropdown.options[millDropdown.selectedIndex].textContent;
    const machineName = machineDropdown.options[machineDropdown.selectedIndex].textContent;

    const requestData = {
        date,
        defectType,
        millId: millDropdown.value,
        machineId: machineDropdown.value,
        saveDir,
        millName,
        machineName,
    };

    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData),
        });

        const result = await response.json();
        displayResponse(result);
    } catch (error) {
        console.error('Error submitting request:', error);
        displayResponse({ message: `Error: ${error.message}` });
    }
}

function displayResponse(result) {
    const responseDiv = document.getElementById('response');
    responseDiv.innerHTML = ''; // Clear previous response

    if (result.file) {
        // Extract the file name from the full path
        const fileName = result.file.split('/').pop();

        // Create a download button
        const downloadButton = document.createElement('button');
        downloadButton.textContent = 'Download Result File';
        downloadButton.addEventListener('click', () => {
            // Update the URL to use the correct download route
            const downloadUrl = `/download/${encodeURIComponent(fileName)}`;
            window.location.href = downloadUrl;
        });

        responseDiv.appendChild(document.createTextNode(result.message));
        responseDiv.appendChild(document.createElement('br'));
        responseDiv.appendChild(downloadButton);
    } else {
        responseDiv.textContent = result.message || 'An error occurred.';
    }
}

