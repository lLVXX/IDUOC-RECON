// CSRF helper
function getCookie(name) {
  let v = null;
  document.cookie.split(';').forEach(c => {
    c = c.trim();
    if (c.startsWith(name + '=')) v = decodeURIComponent(c.slice(name.length+1));
  });
  return v;
}

const csrftoken     = getCookie('csrftoken');
const btnTransmitir = document.getElementById('btnTransmitir');
const btnFinalizar  = document.getElementById('btnFinalizar');
const video         = document.getElementById('videoFeed');
const canvas        = document.getElementById('canvasCapture');
const ctx           = canvas.getContext('2d');

const detected = new Set();
const captured = new Set();
let ws, streaming = false, intervalId;

const configDiv     = document.getElementById('config');
const wsUrl         = configDiv.dataset.wsUrl;
const asistenciaUrl = configDiv.dataset.asistenciaUrl;
const finishUrl     = configDiv.dataset.finishUrl;
const capturaUrl    = configDiv.dataset.capturaUrl;

console.log("[INIT] detalle_instancia.js cargado");
console.log("[CONFIG] wsUrl:", wsUrl);

// Captura imagen y envía por WebSocket
function captureAndSend() {
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  canvas.toBlob(blob => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(blob);
      console.log("[WS] Frame enviado");
    }
  }, 'image/jpeg', 0.7);
}

// Recibe y procesa coincidencias desde el WebSocket
async function onWsMessage(evt) {
  const payload = JSON.parse(evt.data);
  const matches = payload.matches || [];

  console.log(`[WS] ${matches.length} coincidencia(s) recibida(s)`);

  for (const match of matches) {
    const id = match.match_id;
    if (id != null && !detected.has(id)) {
      detected.add(id);
      console.log(`[MATCH] ID=${id} | Similitud=${match.similarity?.toFixed(4)}`);

      // Actualizar UI
      const card  = document.getElementById(`card-${id}`);
      const badge = card?.querySelector('.badge');
      if (card && badge) {
        badge.textContent = 'Presente';
        badge.classList.remove('bg-secondary');
        badge.classList.add('bg-success');
        console.log(`[UI] Estudiante ${id} marcado como presente en la interfaz`);
      } else {
        console.warn(`[UI] No se encontró la tarjeta para el estudiante ${id}`);
      }

      // Registrar asistencia
      try {
        const res = await fetch(asistenciaUrl, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ estudiante: id })
        });
        const json = await res.json();
        console.log(`[API] Asistencia enviada para ${id}`, json);
      } catch (err) {
        console.error(`[API] Error al registrar asistencia de ${id}`, err);
      }

      btnFinalizar.disabled = false;

      // Capturar imagen dinámica
      if (!captured.has(id)) {
        captured.add(id);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imgB64 = canvas.toDataURL('image/jpeg', 0.8);

        try {
          const res = await fetch(capturaUrl, {
            method: 'POST',
            headers: {
              'X-CSRFToken': csrftoken,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ estudiante_id: id, imagen_b64: imgB64 })
          });
          console.log(`[IMG] Foto dinámica enviada para ${id}`, await res.json());
        } catch (err) {
          console.error(`[IMG ERROR] Error al enviar imagen de ${id}`, err);
        }
      }
    }
  }
}

// Iniciar transmisión
btnTransmitir.addEventListener('click', async () => {
  if (!streaming) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      await video.play();

      ws = new WebSocket(wsUrl);
      ws.onopen    = () => console.log('[WS] Conectado');
      ws.onmessage = onWsMessage;

      intervalId = setInterval(captureAndSend, 300);
      streaming  = true;

      btnTransmitir.textContent = 'Detener transmisión';
      btnTransmitir.classList.replace('btn-primary', 'btn-danger');
    } catch (err) {
      console.error('[CAM] Error al iniciar cámara', err);
      alert('Error al iniciar cámara');
    }
  } else {
    clearInterval(intervalId);
    ws?.close();
    streaming = false;
    video.srcObject?.getTracks().forEach(t => t.stop());
    btnTransmitir.textContent = 'Iniciar transmisión';
    btnTransmitir.classList.replace('btn-danger', 'btn-primary');
  }
});

// Finalizar clase
btnFinalizar.addEventListener('click', async () => {
  console.log("[FIN] Finalizando clase...");

  if (streaming) {
    clearInterval(intervalId);
    ws?.close();
    streaming = false;
    video.srcObject?.getTracks().forEach(t => t.stop());
  }

  for (const id of detected) {
    if (!captured.has(id)) {
      captured.add(id);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imgB64 = canvas.toDataURL('image/jpeg', 0.8);
      try {
        const res = await fetch(capturaUrl, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ estudiante_id: id, imagen_b64: imgB64 })
        });
        console.log(`[IMG-FIN] Foto final enviada para ${id}`, await res.json());
      } catch (err) {
        console.error(`[IMG-FIN ERROR] Error captura final ${id}`, err);
      }
    }
  }

  try {
    const res = await fetch(finishUrl, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrftoken }
    });
    const json = await res.json();
    if (json.ok) {
      window.location.href = json.url_reporte;
    } else {
      alert("Error al finalizar clase");
    }
  } catch (err) {
    console.error("[FIN ERROR]", err);
    alert("Fallo al cerrar clase");
  }
});