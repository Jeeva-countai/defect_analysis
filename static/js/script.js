document.addEventListener('DOMContentLoaded', () => {
    fetchMills();
    document.getElementById('millDropdown').addEventListener('change', fetchMachines);
    document.getElementById('submitButton').addEventListener('click', handleSubmit);
});

async function fetchMills() {
    const responseDiv = document.getElementById('response');
    responseDiv.innerHTML = ''; // Clear previous response

    try {
        console.log('Fetching mills...');
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
            console.log('Mills loaded:', data.mills);
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
            console.log(`Fetching machines for mill ID: ${millId}`);
            const response = await fetch(`/get_machines/${millId}`);
            const data = await response.json();
            if (data.machines && data.machines.length > 0) {
                data.machines.forEach(machine => {
                    const option = document.createElement('option');
                    option.value = machine.machinedetail_id;
                    option.textContent = machine.machine_name;
                    machineDropdown.appendChild(option);
                });
                console.log('Machines loaded:', data.machines);
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

    const millName = millDropdown.options[millDropdown.selectedIndex].textContent; // Get mill name
    const machineName = machineDropdown.options[machineDropdown.selectedIndex].textContent; // Get machine name
    const millId = millDropdown.value;
    const machineId = machineDropdown.value;

    let clientIp = '127.0.0.1'; // Default fallback IP address

    // Fetch client IP dynamically or use a placeholder (if needed).
    try {
        console.log('Fetching client IP...');
        const ipResponse = await fetch('/get_client_ip');
        const ipData = await ipResponse.json();
        clientIp = ipData.client_ip || clientIp; // Use fetched IP or fallback.
        console.log('Client IP:', clientIp);
    } catch (error) {
        console.error('Error fetching client IP:', error);
    }

    const requestData = {
        date,
        defectType,
        millId,
        machineId,
        saveDir,
        millName, // Include mill name
        machineName, // Include machine name
        client_ip: clientIp,
    };

    try {
        console.log('Submitting request data:', requestData);
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
        // Create a Download Button
        const downloadButton = document.createElement('button');
        downloadButton.textContent = 'Download Result File';
        downloadButton.addEventListener('click', () => {
            const downloadUrl = `/download/${result.date}/${result.defectTypeId}`;
            window.location.href = downloadUrl;
        });

        responseDiv.appendChild(document.createTextNode(result.message));
        responseDiv.appendChild(document.createElement('br'));
        responseDiv.appendChild(downloadButton);

        console.log('Response with file:', result);
    } else {
        responseDiv.innerText = `${result.message}`;
        console.error(result.message); // Log errors to console.
    }
}

// Handle direct download button click
submitButton.addEventListener('click', async (event) => {
    event.preventDefault();
    const dateInput = document.getElementById('date');
    const defectTypeInput = document.getElementById('defectType');
    const responseDiv = document.getElementById('response');

    try {
        const response = await fetch('/download', {
            method: 'POST',
            body: JSON.stringify({
                date: dateInput.value,
                defect_type_id: defectTypeInput.value,
            }),
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (response.ok) {
            // Create a download button
            const downloadButton = document.createElement('button');
            downloadButton.textContent = 'Download Result File';
            downloadButton.addEventListener('click', () => {
                const downloadUrl = `/download/${dateInput.value}/${defectTypeInput.value}`;
                window.location.href = downloadUrl;
            });
            responseDiv.appendChild(document.createElement('br'));
            responseDiv.appendChild(downloadButton);
        } else {
            responseDiv.textContent = data.message || 'Failed to process the request.';
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        responseDiv.textContent = 'An error occurred while submitting the form.';
    }
});
