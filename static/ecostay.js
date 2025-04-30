let map;
let markers = [];
let currentStays = [];

function initMap() {
  map = new google.maps.Map(document.getElementById("google-map"), {
    center: { lat: 12.9716, lng: 77.5946 }, // Bangalore coordinates
    zoom: 8,
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const citySelect = document.getElementById("city");

  // Fetch available cities from the JSON data
  fetch("/eco-stays/cities")
    .then((response) => response.json())
    .then((data) => {
      if (data.cities) {
        data.cities.forEach((city) => {
          const option = document.createElement("option");
          option.value = city.toLowerCase();
          // Capitalize first letter of each word
          option.textContent = city
            .split("_")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
          citySelect.appendChild(option);
        });
      }
    })
    .catch((error) => console.error("Error loading cities:", error));

  const staysGrid = document.getElementById("stays-grid");
  const mapView = document.getElementById("map-container");
  const resultsSection = document.getElementById("results-section");
  const cityNameSpan = document.getElementById("city-name");
  const loading = document.createElement("div");
  loading.id = "loading";
  loading.innerHTML = "Loading...";
  loading.style.display = "none";
  document.body.appendChild(loading);

  // View toggle handlers
  document.querySelectorAll(".view-button").forEach((button) => {
    button.addEventListener("click", function () {
      document
        .querySelectorAll(".view-button")
        .forEach((b) => b.classList.remove("active"));
      this.classList.add("active");

      if (this.dataset.view === "map") {
        staysGrid.style.display = "none";
        mapView.classList.add("active");
        if (map) {
          google.maps.event.trigger(map, "resize");
        }
      } else {
        staysGrid.style.display = "grid";
        mapView.classList.remove("active");
      }
    });
  });

  // Category filter handlers
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", function () {
      document
        .querySelectorAll(".tab-button")
        .forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
      filterStays(this.dataset.category);
    });
  });

  // City selection handler
  citySelect.addEventListener("change", async function () {
    if (!this.value) return;

    loading.style.display = "block";
    staysGrid.innerHTML = "";

    try {
      const response = await fetch(`/eco-stays?city=${this.value}`);
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      currentStays = data.eco_stays;
      resultsSection.classList.remove("hidden");
      cityNameSpan.textContent =
        this.value.charAt(0).toUpperCase() + this.value.slice(1);
      displayStays(currentStays);
      updateMapMarkers(currentStays);
    } catch (error) {
      console.error("Error fetching eco-stays:", error);
      staysGrid.innerHTML = `<p class="error">Failed to load eco-stays. Please try again.</p>`;
    } finally {
      loading.style.display = "none";
    }
  });
});

function displayStays(stays) {
  const staysGrid = document.getElementById("stays-grid");
  const mapList = document.getElementById("map-list");

  if (!staysGrid || !mapList) return;

  staysGrid.innerHTML = "";
  mapList.innerHTML = "";

  stays.forEach((stay) => {
    // Grid view card
    const card = createStayCard(stay);
    staysGrid.appendChild(card);

    // Map list item
    const listItem = createMapListItem(stay);
    mapList.appendChild(listItem);
  });
}

function createStayCard(stay) {
  const card = document.createElement("div");
  card.className = "stay-card";
  const placeholderImage = "/static/images/placeholder.jpg";

  card.innerHTML = `
      <div class="stay-image">
          <img src="${stay.image_url}" 
               alt="${stay.name}"
               onerror="this.src='${placeholderImage}'; this.classList.add('placeholder')"
               onload="this.classList.remove('loading')">
      </div>
      <div class="stay-details">
          <h3 class="stay-name">${stay.name}</h3>
          <p class="stay-location">${stay.location}</p>
          <div class="stay-features">
              <h4>Eco Features</h4>
              <ul class="eco-features-list">
                  ${stay.eco_features
                    .map((feature) => `<li>${feature}</li>`)
                    .join("")}
              </ul>
          </div>
          <div class="stay-amenities">
              <h4>Amenities</h4>
              <ul class="amenities-list">
                  ${stay.amenities
                    .map((amenity) => `<li>${amenity}</li>`)
                    .join("")}
              </ul>
          </div>
          <p class="stay-price">${stay.price_range}</p>
          <a href="${
            stay.source_url
          }" class="btn view-source" target="_blank">View Details</a>
      </div>
  `;
  return card;
}

function createMapListItem(stay) {
  const item = document.createElement("div");
  item.className = "map-list-item";
  const placeholderImage = "/static/images/placeholder.jpg";

  item.innerHTML = `
        <div class="map-list-image">
            <img src="${stay.image_url}" 
                 alt="${stay.name}"
                 onerror="this.src='${placeholderImage}'; this.classList.add('placeholder')"
                 onload="this.classList.remove('loading')">
        </div>
        <div class="map-list-content">
            <h3>${stay.name}</h3>
            <p>${stay.location}</p>
            <p class="map-list-price">${stay.price_range}</p>
        </div>
    `;
  return item;
}

function updateMapMarkers(stays) {
  // Clear existing markers
  markers.forEach((marker) => marker.setMap(null));
  markers = [];

  // Add new markers
  stays.forEach((stay) => {
    if (!stay.coordinates) return;

    const marker = new google.maps.Marker({
      map: map,
      position: { lat: stay.coordinates.lat, lng: stay.coordinates.lng },
      title: stay.name,
    });

    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div class="map-info-window">
          <h3>${stay.name}</h3>
          <p>${stay.location}</p>
          <p>${stay.price_range}</p>
        </div>
      `,
    });

    marker.addListener("click", () => {
      infoWindow.open(map, marker);
    });

    markers.push(marker);
  });

  // Adjust map bounds to show all markers
  if (markers.length > 0) {
    const bounds = new google.maps.LatLngBounds();
    markers.forEach((marker) => bounds.extend(marker.getPosition()));
    map.fitBounds(bounds);
  }
}

function filterStays(category) {
  if (category === "all") {
    displayStays(currentStays);
    updateMapMarkers(currentStays);
    return;
  }

  const filteredStays = currentStays.filter((stay) => {
    const name = stay.name.toLowerCase();

    switch (category) {
      case "hotels":
        return (
          name.includes("hotel") ||
          name.includes("suite") ||
          name.includes("residenc")
        );

      case "resorts":
        return name.includes("resort");

      case "homestays":
        return (
          name.includes("b&b") ||
          name.includes("homestay") ||
          name.includes("cottage") ||
          name.includes("villa") ||
          // If it doesn't match any other category, consider it a homestay
          (!name.includes("hotel") &&
            !name.includes("suite") &&
            !name.includes("residenc") &&
            !name.includes("resort"))
        );

      default:
        return true;
    }
  });

  displayStays(filteredStays);
  updateMapMarkers(filteredStays);
}
