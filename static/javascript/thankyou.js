// Check if PDF exists and enable button when ready
(function () {
  const button = document.getElementById("whatsappButton");
  const maxRetries = 5;
  let retryCount = 0;

  async function checkPdfExists(url) {
    try {
      const response = await fetch(url, { method: "HEAD" });
      return response.ok;
    } catch (error) {
      console.error("Error checking PDF:", error);
      return false;
    }
  }

  async function retryPdfCheck() {
    if (retryCount >= maxRetries) {
      button.disabled = false;
      return;
    }

    const exists = await checkPdfExists(pdfUrl);
    if (exists) {
      button.disabled = false;
      return;
    }

    retryCount++;
    setTimeout(retryPdfCheck, 2000);
  }

  // Start checking for PDF
  retryPdfCheck();
})();

// Send WhatsApp message
function sendWhatsAppMessage() {
  const button = document.getElementById("whatsappButton");
  button.disabled = true;

  try {
    const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(
      message
    )}`;
    const whatsappWindow = window.open(whatsappUrl, "_blank");

    if (!whatsappWindow) {
      alert("Please allow popups to open WhatsApp");
    }

    // Re-enable button after delay
    setTimeout(() => {
      button.disabled = false;
    }, 3000);
  } catch (error) {
    console.error("Error sending WhatsApp message:", error);
    alert("There was an error opening WhatsApp. Please try again.");
    button.disabled = false;
  }
}

// Handle back navigation
window.addEventListener("pageshow", function (event) {
  const button = document.getElementById("whatsappButton");
  if (
    event.persisted ||
    (window.performance && window.performance.navigation.type === 2)
  ) {
    setTimeout(() => {
      button.disabled = false;
    }, 1000);
  }
});
