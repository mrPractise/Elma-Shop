(function () {
  const pdfUrl = "{{ pdf_url|escapejs }}";
  const button = document.getElementById("whatsappButton");
  const maxRetries = 5;
  let retryCount = 0;

  // Function to check if PDF exists
  async function checkPdfExists(url) {
    try {
      const response = await fetch(url, { method: "HEAD" });
      return response.ok;
    } catch (error) {
      console.error("Error checking PDF:", error);
      return false;
    }
  }

  // Function to retry PDF check
  async function retryPdfCheck() {
    if (retryCount >= maxRetries) {
      button.disabled = false;
      alert(
        "PDF generation is taking longer than expected. You can try sending the order now, but the PDF might not be ready."
      );
      return;
    }

    const exists = await checkPdfExists(pdfUrl);
    if (exists) {
      button.disabled = false;
      return;
    }

    retryCount++;
    setTimeout(retryPdfCheck, 2000); // Retry every 2 seconds
  }

  // Start checking for PDF
  retryPdfCheck();
})();

function sendWhatsAppMessage() {
  const button = document.getElementById("whatsappButton");
  button.disabled = true;

  try {
    const phoneNumber = "{{ whatsapp_number }}".replace(/[^0-9]/g, "");
    const message = "{{ whatsapp_message|escapejs }}";

    if (!phoneNumber) {
      throw new Error("WhatsApp number is not configured");
    }

    // Store timestamp in localStorage
    localStorage.setItem("lastWhatsAppSend", Date.now());

    // Construct and open WhatsApp URL
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
    alert(
      "There was an error opening WhatsApp. Please try again or contact support."
    );
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
    // Page was restored from back/forward cache
    const lastSend = localStorage.getItem("lastWhatsAppSend");
    if (lastSend && Date.now() - parseInt(lastSend) < 60000) {
      // If less than 1 minute has passed, keep button disabled
      button.disabled = true;
      setTimeout(() => {
        button.disabled = false;
      }, 3000);
    }
  }
});
