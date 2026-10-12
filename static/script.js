const $ = id => document.getElementById(id);

async function loadDashboard() {
    try {
        const response = await fetch("/api/dashboard");
        const data = await response.json();

        if (!response.ok) throw new Error(data.error);

        $("donorCount").textContent = data.donor_count;
        $("unitCount").textContent = data.units;
        $("requestCount").textContent = data.request_count;

        $("inventory").innerHTML = data.inventory.map(item => `
            <div class="blood-card">
                <b>${item.blood_group}</b>
                <h3>${item.units}</h3>
                <small>Units available</small>
            </div>
        `).join("");

        $("donorRows").innerHTML = data.donors.map(d => `
            <tr>
                <td>${escapeText(d.name)}</td>
                <td>${escapeText(d.blood_group)}</td>
                <td>${d.age}</td>
                <td>${escapeText(d.city)}</td>
                <td>${escapeText(d.phone)}</td>
            </tr>
        `).join("");
    } catch (error) {
        $("inventory").textContent =
            "Unable to load data. Check the Flask server.";
    }
}

function escapeText(value) {
    const element = document.createElement("span");
    element.textContent = value ?? "";
    return element.innerHTML;
}

$("donorForm").addEventListener("submit", async event => {
    event.preventDefault();

    const data = Object.fromEntries(new FormData(event.target));
    data.age = Number(data.age);

    const response = await fetch("/api/donors", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    $("donorMessage").textContent =
        result.message || result.error;

    if (response.ok) {
        event.target.reset();
        loadDashboard();
    }
});

$("requestForm").addEventListener("submit", async event => {
    event.preventDefault();

    const data = Object.fromEntries(new FormData(event.target));

    const response = await fetch("/api/requests", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    $("requestMessage").textContent =
        result.message || result.error;

    if (response.ok) {
        event.target.reset();
        loadDashboard();
    }
});

loadDashboard();