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

           // Set initial cart count
    const initialCartCount = {{ request.session|cart_item_count }};
    updateCartCounter(initialCartCount);

    function updateCartCounter(itemCount) {
        const cartCounter = document.querySelector(".cart-counter");
        if (cartCounter) {
            cartCounter.textContent = itemCount;
            cartCounter.style.display = itemCount > 0 ? "block" : "none";
        }
    }



        var searchIcon = document.getElementById('search-icon');
        var searchModal = document.getElementById('search-modal');
        var closeBtn = searchModal.querySelector('.close');

        searchIcon.addEventListener('click', function(e) {
            e.preventDefault();
            searchModal.style.display = 'block';
        });

        closeBtn.addEventListener('click', function() {
            searchModal.style.display = 'none';
        });

        window.addEventListener('click', function(e) {
            if (e.target == searchModal) {
                searchModal.style.display = 'none';
            }
        });
 