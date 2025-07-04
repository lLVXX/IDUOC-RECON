import re
from django.core.exceptions import ValidationError

def validar_rut_chileno(value):
    print("[DEBUG] RUT recibido para validar:", value)  # ← log en consola
    value = value.upper().replace(".", "").replace("-", "")
    if not re.match(r'^\d{7,8}[0-9K]$', value):
        print("[ERROR] Formato incorrecto")
        raise ValidationError("El RUT debe tener el formato XX.XXX.XXX-X")

    cuerpo = value[:-1]
    dv = value[-1]

    suma = 0
    multiplo = 2

    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1  # ciclo correcto 2-7

    resto = suma % 11
    verificador = 11 - resto
    if verificador == 11:
        dv_esperado = "0"
    elif verificador == 10:
        dv_esperado = "K"
    else:
        dv_esperado = str(verificador)

    print(f"[DEBUG] Calculado: {dv_esperado}, Recibido: {dv}")

    if dv != dv_esperado:
        print("[ERROR] RUT inválido: DV no coincide")
        raise ValidationError("RUT inválido")
