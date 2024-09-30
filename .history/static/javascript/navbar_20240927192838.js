document.addEventListener("DOMContentLoaded", function () {
  // Get all navigation items
  const navigationItems = document.querySelectorAll(".navbar ul li a");

  // Function to set active item
  function setActiveItem(item) {
    navigationItems.forEach((navItem) => {
      navItem.classList.remove("active");
    });
    item.classList.add("active");
    localStorage.setItem("activeNavItem", item.getAttribute("data-name"));
  }

  // Set active item on page load
  const activeItemName = localStorage.getItem("activeNavItem");
  if (activeItemName) {
    const activeItem = document.querySelector(
      `[data-name="${activeItemName}"]`
    );
    if (activeItem) {
      setActiveItem(activeItem);
    }
  }

  // Add click event listener to each navigation item
  navigationItems.forEach((item) => {
    item.addEventListener("click", function (event) {
      setActiveItem(event.target);
    });
  });
});
