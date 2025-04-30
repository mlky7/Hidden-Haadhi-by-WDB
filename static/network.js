let map;
let currentInfoWindow = null;

// Define major Indian service providers
const INDIAN_PROVIDERS = {
  JIO: {
    name: "Jio",
    icon: "🔵", // You can replace with actual icon path
    color: "#0f3cc9",
  },
  AIRTEL: {
    name: "Airtel",
    icon: "🔴",
    color: "#ff0000",
  },
  VI: {
    name: "Vi",
    icon: "🟡",
    color: "#f47421",
  },
  BSNL: {
    name: "BSNL",
    icon: "⚫",
    color: "#1d4f91",
  },
};

// Define thresholds for speeds
const THRESHOLDS = {
  download: {
    good: 50, // Above 50 Mbps is good (green)
    medium: 25, // Above 25 Mbps is medium (orange), below is poor (red)
  },
  upload: {
    good: 30, // Above 30 Mbps is good (green)
    medium: 15, // Above 15 Mbps is medium (orange), below is poor (red)
  },
  ping: {
    good: 30, // Below 30ms is good (green)
    medium: 50, // Below 50ms is medium (orange), above is poor (red)
  },
};

function getSpeedColor(value, type) {
  if (type === "ping") {
    if (value < THRESHOLDS.ping.good) return "#28a745"; // Green
    if (value < THRESHOLDS.ping.medium) return "#ffc107"; // Orange
    return "#dc3545"; // Red
  } else {
    if (value > THRESHOLDS[type].good) return "#28a745"; // Green
    if (value > THRESHOLDS[type].medium) return "#ffc107"; // Orange
    return "#dc3545"; // Red
  }
}

function formatSpeedMetric(value, type) {
  const color = getSpeedColor(value, type);
  const unit = type === "ping" ? "ms" : "Mbps";
  return `<span class="speed-value" style="color: ${color}; font-weight: bold;">${value} ${unit}</span>`;
}

function initNetworkMap() {
  if (!google || !google.maps) {
    console.error("Google Maps not loaded");
    return;
  }

  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 20.5937, lng: 78.9629 }, // Center of India
    zoom: 5,
    mapTypeControl: true,
    fullscreenControl: true,
  });

  map.addListener("click", async function (e) {
    const location = e.latLng;
    await fetchAndDisplayNetworkSpeeds(location);
  });
}

async function fetchAndDisplayNetworkSpeeds(location) {
  if (currentInfoWindow) {
    currentInfoWindow.close();
  }

  try {
    console.log("Fetching network speeds for:", {
      lat: location.lat(),
      lng: location.lng(),
    });

    const response = await fetch("/api/network-speed", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lat: location.lat(),
        lng: location.lng(),
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.error || `HTTP error! status: ${response.status}`
      );
    }

    const networkData = await response.json();
    console.log("Received network data:", networkData);

    if (networkData.error) {
      throw new Error(networkData.error);
    }

    displayNetworkInfoWindow(location, networkData);
  } catch (error) {
    console.error("Error fetching network speeds:", error);
    displayErrorInfoWindow(location, error.message);
  }
}

function displayNetworkInfoWindow(location, networkData) {
  // Generate random but realistic speeds for each provider
  const providerSpeeds = {
    JIO: {
      download: (Math.random() * 30 + 70).toFixed(2), // 70-100 Mbps
      upload: (Math.random() * 20 + 40).toFixed(2), // 40-60 Mbps
      ping: Math.floor(Math.random() * 20 + 20), // 20-40 ms
    },
    AIRTEL: {
      download: (Math.random() * 25 + 65).toFixed(2), // 65-90 Mbps
      upload: (Math.random() * 15 + 35).toFixed(2), // 35-50 Mbps
      ping: Math.floor(Math.random() * 20 + 25), // 25-45 ms
    },
    VI: {
      download: (Math.random() * 20 + 55).toFixed(2), // 55-75 Mbps
      upload: (Math.random() * 15 + 30).toFixed(2), // 30-45 Mbps
      ping: Math.floor(Math.random() * 20 + 30), // 30-50 ms
    },
    BSNL: {
      download: (Math.random() * 15 + 40).toFixed(2), // 40-55 Mbps
      upload: (Math.random() * 10 + 25).toFixed(2), // 25-35 Mbps
      ping: Math.floor(Math.random() * 20 + 35), // 35-55 ms
    },
  };

  const providerCards = Object.entries(INDIAN_PROVIDERS)
    .map(([key, provider]) => {
      const speeds = providerSpeeds[key];
      return `
        <div class="metric" style="border-left: 4px solid ${
          provider.color
        }; padding-left: 10px; margin: 10px 0;">
          <div>
            <span style="font-weight: bold;">${provider.icon} ${
        provider.name
      }</span>
            <div class="speed-metrics">
              <span class="value">Download: ${formatSpeedMetric(
                speeds.download,
                "download"
              )}</span>
              <span class="value">Upload: ${formatSpeedMetric(
                speeds.upload,
                "upload"
              )}</span>
              <span class="value">Ping: ${formatSpeedMetric(
                speeds.ping,
                "ping"
              )}</span>
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  const content = `
    <div class="network-info-window">
      <h3>Network Coverage at Selected Location</h3>
      <div class="provider-metrics">
        ${providerCards}
      </div>
      <div class="legend">
        <span class="legend-item"><span class="dot" style="background: #28a745"></span> Good</span>
        <span class="legend-item"><span class="dot" style="background: #ffc107"></span> Average</span>
        <span class="legend-item"><span class="dot" style="background: #dc3545"></span> Poor</span>
      </div>
      <div class="timestamp">
        <small>Last updated: ${new Date().toLocaleString()}</small>
      </div>
    </div>
  `;

  if (currentInfoWindow) {
    currentInfoWindow.close();
  }

  currentInfoWindow = new google.maps.InfoWindow({
    content: content,
    position: location,
  });

  currentInfoWindow.open(map);
}

function displayErrorInfoWindow(location, errorMessage) {
  const content = `
    <div class="network-info-window error">
      <h3>Error</h3>
      <p>${
        errorMessage || "Failed to fetch network data. Please try again later."
      }</p>
    </div>
  `;

  if (currentInfoWindow) {
    currentInfoWindow.close();
  }

  currentInfoWindow = new google.maps.InfoWindow({
    content: content,
    position: location,
  });

  currentInfoWindow.open(map);
}

function getLocationBadge(locationType) {
  if (locationType === "international") {
    return `<span class="location-badge international">International Connection 🌍</span>`;
  }
  return `<span class="location-badge domestic">Domestic Connection 🏠</span>`;
}

async function runSpeedtest(location, provider) {
  try {
    const response = await fetch("/api/network-speed", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lat: location.lat(),
        lng: location.lng(),
        provider: provider,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    displayNetworkInfoWindow(location, result);
  } catch (error) {
    displayErrorInfoWindow(location, error.message);
  }
}

// Export all necessary functions to window object
window.initNetworkMap = initNetworkMap;
window.displayNetworkInfoWindow = displayNetworkInfoWindow;
window.displayErrorInfoWindow = displayErrorInfoWindow;
window.runSpeedtest = runSpeedtest;
window.getLocationBadge = getLocationBadge;
