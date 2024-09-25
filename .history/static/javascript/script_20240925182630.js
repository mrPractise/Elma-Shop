document.addEventListener("DOMContentLoaded", function () {
  // Event listeners for "Add to Cart" buttons
  document.querySelectorAll(".cart-btn").forEach((button) => {
    button.addEventListener("click", function () {
      const productId = this.dataset.productId;
      handleCartAction(`/add-to-cart/${productId}/`, productId);
    });
  });

  // Event listeners for "Remove from Cart" buttons
  document.querySelectorAll(".remove-from-cart").forEach((button) => {
    button.addEventListener("click", function () {
      const productId = this.dataset.productId;
      handleCartAction(`/remove-from-cart/${productId}/`, productId);
    });
  });

  // Event listeners for quantity buttons
  document.querySelectorAll(".quantity-btn").forEach((button) => {
    button.addEventListener("click", function () {
      const productId = this.dataset.productId;
      const isIncrement = this.textContent.trim() === "+";
      const url = isIncrement
        ? `/add-to-cart/${productId}/`
        : `/remove-from-cart/${productId}/`;
      handleCartAction(url, productId);
    });
  });

  function handleCartAction(url, productId, data = {}) {
    fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          updateCartDisplay(
            productId,
            data.quantity,
            data.total_price,
            data.cart_total,
            data.cart_total_items
          );
        }
      })
      .catch((error) => console.error("Error:", error));
  }

  function updateCartDisplay(
    productId,
    quantity,
    totalPrice,
    cartTotal,
    cartTotalItems
  ) {
    // Update product listing
    const productItem = document.querySelector(
      `.product-item[data-product-id="${productId}"]`
    );
    if (productItem) {
      const quantitySpan = productItem.querySelector(".cart-quantity");
      const removeButton = productItem.querySelector(".remove-from-cart");

      if (quantitySpan) quantitySpan.textContent = quantity;
      if (removeButton) {
        removeButton.style.display = quantity > 0 ? "inline-block" : "none";
      }
    }

    // Update cart item quantity and total
    const cartItem = document.querySelector(
      `.cart-item[data-product-id="${productId}"]`
    );
    if (cartItem) {
      const quantitySpan = cartItem.querySelector(".item-quantity span");
      const itemTotal = cartItem.querySelector(".item-total");
      if (quantitySpan) quantitySpan.textContent = quantity;
      if (itemTotal) itemTotal.textContent = `Ksh.${totalPrice}`;
    }

    // Update summary item quantity and total
    const summaryItem = document.querySelector(
      `.summary-item[data-product-id="${productId}"]`
    );
    if (summaryItem) {
      const summaryQuantity = summaryItem.querySelector(
        ".summary-item-quantity"
      );
      const summaryTotal = summaryItem.querySelector(".summary-item-total");
      if (summaryQuantity)
        summaryQuantity.textContent = `Quantity: ${quantity}`;
      if (summaryTotal) summaryTotal.textContent = `Ksh.${totalPrice}`;
    }

    // Update cart total
    const totalElement = document.querySelector(
      ".summary-total span:last-child"
    );
    if (totalElement) totalElement.textContent = `Ksh.${cartTotal}`;

    // Update subtotal
    const subtotalElement = document.querySelector(
      ".summary-subtotal span:last-child"
    );
    if (subtotalElement) subtotalElement.textContent = `Ksh.${cartTotal}`;

    // Update cart counter
    updateCartCounter(cartTotalItems);
  }

  function updateCartCounter(itemCount) {
    const cartCounter = document.querySelector(".cart-counter");
    if (cartCounter) {
      cartCounter.textContent = itemCount;
      cartCounter.style.display = itemCount > 0 ? "block" : "none";
    }
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Initial update of cart counter
  // This assumes you've set initialCartCount in your HTML template
  if (typeof initialCartCount !== "undefined") {
    updateCartCounter(initialCartCount);
  } else {
    console.warn(
      "initialCartCount is not defined. Cart counter may not be initialized correctly."
    );
  }
});
