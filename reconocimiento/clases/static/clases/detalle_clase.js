document.addEventListener("DOMContentLoaded", function () {
  const video = document.getElementById("video");
  const btnIniciar = document.getElementById("btn-iniciar");
  const status = document.getElementById("asistencia-status");

  let interval = null;
  let running = false;

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      video.play();
    } catch (err) {
      alert("No se pudo acceder a la cámara.");
    }
  }

  async function capturarYEnviarFrame() {
    if (!video.srcObject) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
      let formData = new FormData();
      formData.append("frame", blob);
      status.innerText = "Procesando asistencia...";
      const claseId = window.location.pathname.split("/").filter(Boolean).pop();
      const resp = await fetch(`/clases/ajax-asistencia-live/${claseId}/`, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": getCookie("csrftoken") }
      });
      const data = await resp.json();
      if (data.ok) {
        status.innerText = "Asistencia actualizada.";
        // Actualizar cards en la página
        Object.entries(data.data).forEach(([est_id, est_info]) => {
          const card = document.getElementById(`card-${est_id}`);
          const estado = document.getElementById(`estado-${est_id}`);
          if (card && estado) {
            if (est_info.presente) {
              card.classList.remove("border-danger", "border-secondary");
              card.classList.add("border-success");
              estado.className = "badge bg-success";
              estado.innerText = "Presente";
            } else {
              card.classList.remove("border-success", "border-secondary");
              card.classList.add("border-danger");
              estado.className = "badge bg-danger";
              estado.innerText = "Ausente";
            }
          }
        });
      } else {
        status.innerText = data.msg || "Error microservicio.";
      }
    }, "image/jpeg");
  }

  btnIniciar.addEventListener("click", () => {
    if (!running) {
      startCamera();
      interval = setInterval(capturarYEnviarFrame, 2500); // Cada 2.5 seg
      btnIniciar.textContent = "Detener asistencia facial";
      running = true;
    } else {
      let stream = video.srcObject;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        video.srcObject = null;
      }
      clearInterval(interval);
      status.innerText = "";
      btnIniciar.textContent = "Iniciar asistencia facial en vivo";
      running = false;
    }
  });

  // Utilidad para CSRF
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      let cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        let cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
});