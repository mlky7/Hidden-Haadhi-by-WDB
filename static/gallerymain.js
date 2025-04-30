document.addEventListener("DOMContentLoaded", function () {
  // Get elements
  const fileInput = document.getElementById("file-input");
  const preview = document.getElementById("preview");
  const previewContainer = document.getElementById("preview-container");
  const result = document.getElementById("result");
  const predictionText = document.getElementById("prediction-text");
  const confidenceText = document.getElementById("confidence-text");
  const clearGalleryBtn = document.getElementById("clear-gallery-btn");
  const galleryGrid = document.getElementById("gallery-grid");
  const dropZone = document.getElementById("drop-zone");

  // File handling function
  function handleFile(file) {
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file");
      return;
    }

    // Show preview if elements exist
    if (preview && previewContainer) {
      const reader = new FileReader();
      reader.onload = (e) => {
        preview.src = e.target.result;
        previewContainer.style.display = "block";
      };
      reader.readAsDataURL(file);
    }

    const formData = new FormData();
    formData.append("file", file);

    fetch("/predict", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          if (result) result.style.display = "block";
          if (predictionText) {
            predictionText.textContent = `Predicted Place: ${data.prediction}`;
          }
          if (confidenceText) {
            confidenceText.textContent = `Confidence: ${data.confidence}`;
          }
          setTimeout(() => location.reload(), 2000);
        } else {
          alert("Error: " + data.error);
        }
      })
      .catch((error) => {
        alert("Error: " + error);
      });
  }

  // Add file input change handler
  if (fileInput) {
    fileInput.addEventListener("change", function (e) {
      if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
      }
    });
  }

  // Initialize clear gallery functionality if button exists
  if (clearGalleryBtn) {
    clearGalleryBtn.addEventListener("click", function (e) {
      e.preventDefault();
      console.log("Clear gallery button clicked");

      if (
        confirm(
          "Are you sure you want to clear your gallery? This action cannot be undone."
        )
      ) {
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Clearing...';

        fetch("/gallery/clear", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "same-origin",
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              window.location.reload();
            } else {
              throw new Error(data.error || "Failed to clear gallery");
            }
          })
          .catch((error) => {
            console.error("Error clearing gallery:", error);
            alert("Failed to clear gallery: " + error.message);
          })
          .finally(() => {
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-trash"></i> Clear Gallery';
          });
      }
    });
  }

  // Initialize drag and drop if dropZone exists
  if (dropZone) {
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
      if (file && fileInput) {
        fileInput.files = e.dataTransfer.files;
        handleFile(file);
      }
    });

    // Add click handler for dropZone
    dropZone.addEventListener("click", () => {
      if (fileInput) {
        fileInput.click();
      }
    });
  }

  const categoryFilter = document.getElementById("category-filter");

  if (categoryFilter && galleryGrid) {
    categoryFilter.addEventListener("change", filterGalleryByPlace);

    function filterGalleryByPlace() {
      const selectedPlace = categoryFilter.value.toLowerCase();
      const galleryItems = document.querySelectorAll(".gallery-item");
      let hasVisibleItems = false;

      galleryItems.forEach((item) => {
        const itemPrediction = item
          .querySelector("img")
          .alt.toLowerCase()
          .replace(/\s+/g, "_");

        if (!selectedPlace || selectedPlace === "") {
          // Show all items if no place is selected
          item.style.display = "block";
          item.classList.add("fade-in");
          hasVisibleItems = true;
        } else if (itemPrediction === selectedPlace) {
          // Show items that match the selected place
          item.style.display = "block";
          item.classList.add("fade-in");
          hasVisibleItems = true;
        } else {
          // Hide items that don't match
          item.style.display = "none";
          item.classList.remove("fade-in");
        }
      });

      // Handle no results message
      updateNoResultsMessage(hasVisibleItems);

      // Remove animation class after transition
      setTimeout(() => {
        document.querySelectorAll(".gallery-item.fade-in").forEach((item) => {
          item.classList.remove("fade-in");
        });
      }, 500);
    }

    function updateNoResultsMessage(hasVisibleItems) {
      let noResultsMsg = document.getElementById("no-results-message");

      if (!hasVisibleItems) {
        if (!noResultsMsg) {
          noResultsMsg = document.createElement("div");
          noResultsMsg.id = "no-results-message";
          noResultsMsg.className = "no-results-message";
          galleryGrid.parentNode.insertBefore(
            noResultsMsg,
            galleryGrid.nextSibling
          );
        }
        const selectedPlaceName =
          categoryFilter.options[categoryFilter.selectedIndex].text;
        noResultsMsg.textContent = `No images found for ${selectedPlaceName}`;
        noResultsMsg.style.display = "block";
      } else if (noResultsMsg) {
        noResultsMsg.style.display = "none";
      }
    }

    // Initial filter on page load
    filterGalleryByPlace();
  }
});
