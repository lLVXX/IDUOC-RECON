from datetime import date, timedelta

def obtener_semana_actual():
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
    return [inicio_semana + timedelta(days=i) for i in range(5)]  # Lunes a Viernes