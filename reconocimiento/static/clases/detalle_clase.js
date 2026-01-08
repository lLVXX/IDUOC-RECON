
/// RECONOCIMIENTO/detalle_clase.js
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.marcar-asistencia-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const estudianteId = btn.getAttribute('data-estudiante');
            const estado = btn.getAttribute('data-estado');
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            fetch(window.location.pathname + 'marcar-asistencia/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    estudiante_id: estudianteId,
                    estado: estado
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.reload(); // Rápido, para mostrar cambios en los cards y tabla
                } else {
                    alert("Error: " + data.error);
                }
            });
        });
    });
});