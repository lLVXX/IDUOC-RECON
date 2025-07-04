def generar_nombre_seccion(asignatura):
    sufijos = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    existentes = set(asignatura.secciones.values_list('nombre', flat=True))
    for i in range(1, 1000):
        for letra in sufijos:
            nombre = f"{i:03}{letra}"
            if nombre not in existentes:
                return nombre