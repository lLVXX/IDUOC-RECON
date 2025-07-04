# core/helpers/arcface_microservice.py

import requests

MICROSERVICE_URL = "http://localhost:8001/generar_embedding/"  # Cambia si usas otro host/puerto

def obtener_embedding_desde_microservicio(fileobj):
    files = {"file": ("foto.jpg", fileobj, "image/jpeg")}
    try:
        response = requests.post(MICROSERVICE_URL, files=files, timeout=20)
        if response.status_code == 200 and "embedding" in response.json():
            return response.json()["embedding"]
        else:
            print("[ARCFACE MICRO] Error de respuesta:", response.text)
            return None
    except Exception as e:
        print("[ARCFACE MICRO] Error conexión:", str(e))
        return None
