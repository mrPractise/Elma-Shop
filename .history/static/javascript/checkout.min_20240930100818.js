function setSubtotal(e) {
  subtotal = parseFloat(e.replace(/,/g, ""));
}
document.addEventListener("DOMContentLoaded", function () {
  function e() {
    let e = 0;
    for (const n of t)
      if (n.checked) {
        e = parseFloat(n.getAttribute("data-shipping-cost") || 0);
        break;
      }
    o.textContent = e.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    const n = (a + e).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    c.textContent = n;
  }
  const t = document.querySelectorAll('input[name="location"]'),
    n = document.getElementById("id_custom_address"),
    d = document.getElementById("custom-address-field"),
    o = document.getElementById("shipping-cost-value"),
    c = document.getElementById("total-cost-value");
  let a = 0;
  t.forEach((t) => {
    t.addEventListener("change", e);
  }),
    n.addEventListener("change", function () {
      this.checked
        ? ((d.style.display = "block"),
          t.forEach((e) => {
            (e.checked = !1), (e.disabled = !0);
          }))
        : ((d.style.display = "none"),
          t.forEach((e) => {
            e.disabled = !1;
          })),
        e();
    }),
    e();
});
