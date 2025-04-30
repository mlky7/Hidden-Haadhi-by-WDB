document.addEventListener("DOMContentLoaded", function () {
  // Existing elements
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("photo-input");
  const preview = document.getElementById("preview");
  const result = document.getElementById("result");

  // New elements
  const addPhotoBtn = document.getElementById("add-photo-btn");
  const viewGalleryBtn = document.getElementById("view-gallery-btn");
  const uploadSection = document.getElementById("upload-section");
  const galleryGrid = document.getElementById("gallery-grid");

  // Add filter functionality
  const categoryFilter = document.getElementById("category-filter");
  const locationFilter = document.getElementById("location-filter");

  function filterGallery() {
    const selectedCategory = categoryFilter.value.toLowerCase();
    const selectedLocation = locationFilter.value;
    const galleryItems = document.querySelectorAll(".gallery-item");

    galleryItems.forEach((item) => {
      const itemCategory = item.dataset.category.toLowerCase();
      const itemLocation = item.dataset.location;

      const categoryMatch =
        !selectedCategory || itemCategory === selectedCategory;
      const locationMatch =
        !selectedLocation || itemLocation === selectedLocation;

      if (categoryMatch && locationMatch) {
        item.classList.remove("hidden");
      } else {
        item.classList.add("hidden");
      }
    });
  }

  categoryFilter.addEventListener("change", filterGallery);
  locationFilter.addEventListener("change", filterGallery);

  // Gallery state management
  let userGallery = [];

  // Button click handlers
  addPhotoBtn.addEventListener("click", () => {
    uploadSection.classList.remove("d-none");
    galleryGrid.classList.add("d-none");
    fileInput.click();
  });

  viewGalleryBtn.addEventListener("click", () => {
    uploadSection.classList.add("d-none");
    galleryGrid.classList.remove("d-none");
    loadGallery();
  });

  // Existing file handling logic
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    handleFile(file);
  });

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    handleFile(file);
  });

  function handleFile(file) {
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.style.display = "block";
    };
    reader.readAsDataURL(file);

    uploadAndClassify(file);
  }

  function uploadAndClassify(file) {
    const formData = new FormData();
    formData.append("file", file);

    result.style.display = "none";

    fetch("/predict", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          result.style.display = "block";
          document.getElementById(
            "prediction-text"
          ).textContent = `Predicted Place: ${data.prediction}`;
          document.getElementById(
            "confidence-text"
          ).textContent = `Confidence: ${data.confidence}`;

          // Add to gallery with location
          addToGallery({
            image: preview.src,
            prediction: data.prediction,
            confidence: data.confidence,
            location: data.location,
            timestamp: new Date().toISOString(),
          });
        } else {
          alert("Error: " + data.error);
        }
      })
      .catch((error) => {
        alert("Error: " + error);
      });
  }

  function addToGallery(item) {
    userGallery.push(item);
    localStorage.setItem("userGallery", JSON.stringify(userGallery));

    const galleryItem = createGalleryItem(item);
    galleryGrid.appendChild(galleryItem);
    filterGallery(); // Apply current filters to new item
  }

  function loadGallery() {
    // Load from localStorage or your backend
    userGallery = JSON.parse(localStorage.getItem("userGallery") || "[]");

    galleryGrid.innerHTML = "";
    userGallery.forEach((item) => {
      const galleryItem = createGalleryItem(item);
      galleryGrid.appendChild(galleryItem);
    });
  }

  function createGalleryItem(item) {
    const div = document.createElement("div");
    div.className = "gallery-item";
    div.dataset.location = item.location || "Other";
    div.dataset.category = item.prediction.toLowerCase().replace(/ /g, "_");

    div.innerHTML = `
      <img src="${item.image}" alt="${item.prediction}">
      <div class="gallery-item-info">
        <h6>${item.prediction}</h6>
        <p class="mb-0">
          Location: ${item.location || "Other"}<br>
          Confidence: ${item.confidence}<br>
          <small>${new Date(item.timestamp).toLocaleString()}</small>
        </p>
      </div>
    `;
    return div;
  }

  // Initial load
  loadGallery();
  filterGallery();
});
