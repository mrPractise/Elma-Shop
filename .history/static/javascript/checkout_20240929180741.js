document.addEventListener("DOMContentLoaded", function () {
  const locationOptions = document.querySelectorAll('input[name="location"]');
  const customAddressCheckbox = document.getElementById("id_custom_address");
  const customAddressField = document.getElementById("custom-address-field");
  const shippingCostDisplay = document.getElementById("shipping-cost-value");
  const totalCostDisplay = document.getElementById("total-cost-value");
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
        option.checked = !1;
        option.disabled = !0;
      });
    } else {
      customAddressField.style.display = "none";
      locationOptions.forEach((option) => {
        option.disabled = !1;
      });
    }
    updateShippingCost();
  });
  updateShippingCost();
});
function setSubtotal(value) {
  subtotal = parseFloat(value.replace(/,/g, ""));
}
