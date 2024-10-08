document.addEventListener("DOMContentLoaded", function () {
  const locationOptions = document.querySelectorAll('input[name="location"]');
  const customAddressCheckbox = document.getElementById("id_custom_address");
  const customAddressField = document.getElementById("custom-address-field");
  const shippingCostDisplay = document.getElementById("shipping-cost-value");
  const totalCostDisplay = document.getElementById("total-cost-value");

  // Add this new code for the loading spinner
  const checkoutForm = document.getElementById("checkout-form");
  const loadingOverlay = document.getElementById("loading-overlay");

  checkoutForm.addEventListener("submit", function (e) {
    // Show loading overlay when form is submitted
    loadingOverlay.style.display = "flex";
  });

  // We'll set this value in the HTML
  let subtotal = 0;

  function updateShippingCost() {
    let shippingCost = 0;
    for (const option of locationOptions) {
      if (option.checked) {
        shippingCost = parseFloat(
          option.getAttribute("data-shipping-cost") || 0
        );
        break;
      }
    }
    shippingCostDisplay.textContent = shippingCost
      .toFixed(2)
      .replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    const total = (subtotal + shippingCost)
      .toFixed(2)
      .replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    totalCostDisplay.textContent = total;
  }

  locationOptions.forEach((option) => {
    option.addEventListener("change", updateShippingCost);
  });

  customAddressCheckbox.addEventListener("change", function () {
    if (this.checked) {
      customAddressField.style.display = "block";
      locationOptions.forEach((option) => {
        option.checked = false;
        option.disabled = true;
      });
    } else {
      customAddressField.style.display = "none";
      locationOptions.forEach((option) => {
        option.disabled = false;
      });
    }
    updateShippingCost();
  });

  // Initialize
  updateShippingCost();
});

// Function to set the subtotal from the template
function setSubtotal(value) {
  subtotal = parseFloat(value.replace(/,/g, ""));
}
