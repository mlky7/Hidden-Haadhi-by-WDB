// Make sure this is at the very beginning of the file
window.initializeMap = initializeMap;

// Global variables
let map;
let directionsService;
let directionsRenderer;
let originAutocomplete;
let destinationAutocomplete;
let panorama;
let hiddenPlacesVisible = false;
let hiddenPlacesMarkers = [];
let currentInfoWindow = null;
let streetViewService;

// Famous places in Karnataka with their coordinates
const famousPlaces = [
  {
    name: "Mysore Palace",
    position: { lat: 12.3052, lng: 76.6552 },
    description: "Historic royal palace",
  },
  {
    name: "Hampi Ruins",
    position: { lat: 15.335, lng: 76.46 },
    description: "UNESCO World Heritage Site",
  },
  {
    name: "Jog Falls",
    position: { lat: 14.2244, lng: 74.7873 },
    description: "Second highest plunge waterfall in India",
  },
  {
    name: "Coorg",
    position: { lat: 12.4244, lng: 75.7382 },
    description: "Scotland of India",
  },
  {
    name: "Gol Gumbaz",
    position: { lat: 16.8302, lng: 75.7282 },
    description: "Second largest dome in the world",
  },
];

function initializeMap() {
  const mapElement = document.getElementById("map");
  if (!mapElement) return;

  map = new google.maps.Map(mapElement, {
    center: { lat: 12.9716, lng: 76.5946 },
    zoom: 7,
    mapTypeControl: true,
    fullscreenControl: true,
  });

  // Initialize Street View
  panorama = map.getStreetView();

  directionsService = new google.maps.DirectionsService();
  directionsRenderer = new google.maps.DirectionsRenderer({
    map: map,
    panel: document.getElementById("route-details"),
  });

  // Add markers for famous places
  initializeFamousPlaces();

  // Initialize autocomplete
  const originInput = document.getElementById("origin");
  const destinationInput = document.getElementById("destination");

  if (originInput && destinationInput) {
    originAutocomplete = new google.maps.places.Autocomplete(originInput);
    destinationAutocomplete = new google.maps.places.Autocomplete(
      destinationInput
    );
  }

  loadHiddenPlaces();
}

function createInfoWindowContent(place, city) {
  const coordinates = place.coordinates || place.position; // Handle both types of markers

  let content = `
    <div class="place-info" style="max-width: 300px; text-align: center;">
      <h3 style="margin-bottom: 10px;">${place.name}</h3>`;

  if (place.imageUrl) {
    content += `
      <img src="${place.imageUrl}" 
           alt="${place.name}" 
           style="width: 200px; height: 150px; object-fit: cover; margin: 10px 0; border-radius: 8px;"
           onerror="this.style.display='none'"
      />`;
  }

  content += `
      <p style="margin: 10px 0;">${place.description || ""}</p>
      <button 
        onclick="showStreetView(${coordinates.lat}, ${coordinates.lng})"
        style="
          background: #4CAF50;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          margin-top: 10px;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        "
      >
        <svg style="width: 16px; height: 16px;" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
        Street View
      </button>
    </div>`;

  return content;
}

async function loadHiddenPlaces() {
  try {
    const response = await fetch("/api/places");
    const data = await response.json();

    for (const city of data.cities) {
      for (const place of city.places) {
        const marker = new google.maps.Marker({
          position: place.coordinates,
          map: null,
          title: place.name,
          icon: "http://maps.google.com/mapfiles/ms/icons/green-dot.png",
        });

        const infoWindowContent = await createInfoWindowContent(
          place,
          city.city
        );
        const infoWindow = new google.maps.InfoWindow({
          content: infoWindowContent,
        });

        marker.addListener("click", () => {
          if (currentInfoWindow) currentInfoWindow.close();
          currentInfoWindow = infoWindow;
          infoWindow.open(map, marker);
        });

        hiddenPlacesMarkers.push(marker);
      }
    }
  } catch (error) {
    console.error("Error loading hidden places:", error);
  }
}

async function initializeFamousPlaces() {
  famousPlaces.forEach(async (place) => {
    const marker = new google.maps.Marker({
      position: place.position,
      map: map,
      title: place.name,
      icon: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
    });

    const infoWindowContent = await createInfoWindowContent(
      {
        name: place.name,
        description: place.description,
        coordinates: place.position,
      },
      "famous"
    );

    const infoWindow = new google.maps.InfoWindow({
      content: infoWindowContent,
    });

    marker.addListener("click", () => {
      if (currentInfoWindow) currentInfoWindow.close();
      currentInfoWindow = infoWindow;
      infoWindow.open(map, marker);
    });
  });
}

// Add event listener for the toggle button
document
  .getElementById("showHiddenSpots")
  .addEventListener("change", function () {
    hiddenPlacesVisible = this.checked;
    hiddenPlacesMarkers.forEach((marker) => {
      marker.setMap(hiddenPlacesVisible ? map : null);
    });
  });

function showStreetView(lat, lng) {
  const position = { lat: lat, lng: lng };

  if (!streetViewService) {
    streetViewService = new google.maps.StreetViewService();
  }

  streetViewService.getPanorama(
    {
      location: position,
      radius: 50, // Search radius in meters
      source: google.maps.StreetViewSource.OUTDOOR,
    },
    (data, status) => {
      if (status === google.maps.StreetViewStatus.OK) {
        // Street View is available, show it
        if (!panorama) {
          panorama = map.getStreetView();
        }
        panorama.setPosition(position);
        panorama.setPov({
          heading: 34,
          pitch: 10,
        });
        panorama.setVisible(true);
      } else {
        // Street View is not available, show popup message
        const popup = document.createElement("div");
        popup.className = "street-view-popup";
        popup.innerHTML = "Street View not available at this location";
        popup.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: #333;
          color: white;
          padding: 15px 25px;
          border-radius: 5px;
          z-index: 1000;
          animation: fadeInOut 2s forwards;
        `;

        // Add animation keyframes
        const style = document.createElement("style");
        style.textContent = `
          @keyframes fadeInOut {
            0% { opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { opacity: 0; }
          }
        `;
        document.head.appendChild(style);

        // Add popup to body
        document.body.appendChild(popup);

        // Remove popup after animation
        setTimeout(() => {
          popup.remove();
          style.remove();
        }, 2000);
      }
    }
  );
}

async function fetchAQI(lat, lng) {
  try {
    const response = await fetch(`/get-aqi/${lat}/${lng}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.error || `HTTP error! status: ${response.status}`
      );
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching AQI:", error);
    return {
      error: true,
      message: error.message || "Failed to fetch AQI data",
    };
  }
}

function calculateRoute() {
  const origin = document.getElementById("origin").value;
  const destination = document.getElementById("destination").value;
  const mode = document.getElementById("mode").value;

  if (!origin || !destination) {
    alert("Please enter both origin and destination");
    return;
  }

  const request = {
    origin: origin,
    destination: destination,
    travelMode: google.maps.TravelMode[mode.toUpperCase()],
  };

  directionsService.route(request, (result, status) => {
    if (status === "OK") {
      directionsRenderer.setDirections(result);
      const route = result.routes[0];

      // Update route details
      document.getElementById("routeDetails").value = JSON.stringify(route);
      document.getElementById("routeOrigin").value = origin;
      document.getElementById("routeDestination").value = destination;
      document.getElementById("routeMode").value = mode;
      document.getElementById("routeSummary").value = route.summary;

      // Show the email form
      showEmailForm();

      // Display route information
      displayRouteInfo(route);
    } else {
      alert("Could not calculate route: " + status);
    }
  });
}

function showEmailForm() {
  const emailSection = document.getElementById("emailSection");
  if (emailSection) {
    emailSection.style.display = "block";
  } else {
    console.error("Email section element not found");
  }
}

// Add event listener for form submission
document.addEventListener("DOMContentLoaded", function () {
  const routeEmailForm = document.getElementById("routeEmailForm");
  if (routeEmailForm) {
    routeEmailForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const formData = new FormData(this);

      fetch("/send-route-details", {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          const messageContainer = document.getElementById("emailMessage");
          if (data.success) {
            messageContainer.innerHTML =
              '<div class="alert alert-success">Route details sent successfully!</div>';
            document.getElementById("routeEmail").value = "";
          } else {
            messageContainer.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
          }
        })
        .catch((error) => {
          document.getElementById("emailMessage").innerHTML =
            '<div class="alert alert-danger">An error occurred while sending the email.</div>';
        });
    });
  }
});

function displayRouteInfo(route) {
  const distance = route.legs[0].distance.text;
  const duration = route.legs[0].duration.text;
  const distanceInKm = parseFloat(distance.replace(" km", ""));

  // Emissions calculations
  const emissionsData = {
    DRIVING: { factor: 0.192, label: "Car (Petrol)" },
    TRANSIT: { factor: 0.041, label: "Public Transit" },
    BICYCLING: { factor: 0, label: "Bicycle" },
    WALKING: { factor: 0, label: "Walking" },
    ELECTRIC_CAR: { factor: 0.053, label: "Electric Car" },
    HYBRID_CAR: { factor: 0.111, label: "Hybrid Car" },
    BUS: { factor: 0.089, label: "Bus" },
    TRAIN: { factor: 0.041, label: "Train" },
  };

  // Generate combined HTML with emissions and AQI
  let summaryHTML = `
    <div class="route-info">
      <h3>Route Summary</h3>
      <p>Distance: ${distance}</p>
      <p>Duration: ${duration}</p>
    </div>
  `;

  // Add AQI information if available
  const destLat = route.legs[0].end_location.lat();
  const destLng = route.legs[0].end_location.lng();
  fetchAQI(destLat, destLng)
    .then((aqiData) => {
      if (aqiData && !aqiData.error) {
        summaryHTML += `
          <div class="aqi-info-panel" style="border-left: 4px solid ${
            aqiData.color
          }">
            <h3>Air Quality at Destination</h3>
            <div class="aqi-value" style="color: ${aqiData.color}">${
          aqiData.category
        }</div>
            <div class="aqi-details">
              <p>PM2.5: ${aqiData.components.pm2_5} μg/m³</p>
              <p>PM10: ${aqiData.components.pm10} μg/m³</p>
              <p>NO2: ${aqiData.components.no2} μg/m³</p>
            </div>
            <div class="aqi-recommendation">
              ${getAQIRecommendation(aqiData.category)}
            </div>
          </div>
        `;
      } else {
        summaryHTML += `
          <div class="aqi-info-panel error">
            <h3>Air Quality Information</h3>
            <p class="error-message">
              ${
                aqiData.message ||
                "Unable to fetch air quality data for this location"
              }
            </p>
          </div>
        `;
      }

      // Add emissions table
      summaryHTML += `
        <h3>Carbon Emissions Comparison</h3>
        <table class="emissions-table">
          <thead>
            <tr>
              <th>Mode of Transport</th>
              <th>CO₂ Emissions (kg)</th>
              <th>Comparison</th>
            </tr>
          </thead>
          <tbody>
      `;

      const selectedModeEmissions = distanceInKm * emissionsData[mode].factor;

      Object.entries(emissionsData).forEach(([transportMode, data]) => {
        const emissions = (distanceInKm * data.factor).toFixed(2);
        const comparison =
          transportMode === mode
            ? "Current Selection"
            : (
                ((emissions - selectedModeEmissions) / selectedModeEmissions) *
                100
              ).toFixed(1);

        const comparisonText =
          transportMode === mode
            ? "<span class='current-mode'>Selected</span>"
            : `${comparison > 0 ? "+" : ""}${comparison}%`;

        summaryHTML += `
          <tr class="${transportMode === mode ? "selected-mode" : ""}">
            <td>${data.label}</td>
            <td>${emissions}</td>
            <td>${comparisonText}</td>
          </tr>
        `;
      });

      summaryHTML += `
          </tbody>
        </table>
      `;

      document.getElementById("route-summary").innerHTML = summaryHTML;
    })
    .catch((error) => {
      console.error("Error fetching AQI:", error);
      document.getElementById("route-summary").innerHTML = `
        <div class="alert alert-danger">Error fetching AQI data. Please try again later.</div>
      `;
    });
}

// Helper function for AQI recommendations
function getAQIRecommendation(category) {
  const recommendations = {
    Good: "Perfect conditions for outdoor activities.",
    Fair: "Good for most outdoor activities. Sensitive individuals should monitor their response.",
    Moderate:
      "Consider reducing prolonged outdoor activities if you experience symptoms.",
    Poor: "Reduce outdoor activities. Sensitive groups should avoid prolonged exposure.",
    "Very Poor":
      "Avoid outdoor activities. Consider using air purifiers indoors.",
  };
  return recommendations[category] || "No specific recommendations available.";
}

// Make functions globally available
window.initializeMap = initializeMap;
window.calculateRoute = calculateRoute;
window.showStreetView = showStreetView;
