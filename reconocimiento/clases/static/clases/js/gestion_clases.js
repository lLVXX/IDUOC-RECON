document.addEventListener("DOMContentLoaded", function() {
    // Dependencia Carrera -> Asignatura
    const carreraSel = document.getElementById('id_carrera');
    if (carreraSel) {
        carreraSel.addEventListener('change', function() {
            const carreraId = this.value;
            fetch(window.GET_ASIGNATURAS_AJAX_URL + '?carrera_id=' + carreraId)
            .then(response => response.json())
            .then(data => {
                let asignaturaSelect = document.getElementById('id_asignatura');
                asignaturaSelect.innerHTML = '<option value="">---------</option>';
                data.forEach(function(asig) {
                    asignaturaSelect.innerHTML += `<option value="${asig.id}">${asig.nombre}</option>`;
                });
                // Limpia secciones
                document.getElementById('id_seccion').innerHTML = '<option value="">---------</option>';
            });
        });
    }

    // Dependencia Asignatura -> Seccion
    const asignaturaSel = document.getElementById('id_asignatura');
    if (asignaturaSel) {
        asignaturaSel.addEventListener('change', function() {
            const asigId = this.value;
            fetch(window.GET_SECCIONES_AJAX_URL + '?asignatura_id=' + asigId)
            .then(response => response.json())
            .then(data => {
                let seccionSelect = document.getElementById('id_seccion');
                seccionSelect.innerHTML = '<option value="">---------</option>';
                data.forEach(function(sec) {
                    seccionSelect.innerHTML += `<option value="${sec.id}">${sec.nombre}</option>`;
                });
            });
        });
    }
});