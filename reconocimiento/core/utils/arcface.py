
import requests

def detectar_estudiantes_en_foto(file_obj, endpoint='http://localhost:8001/match_faces/'):
    """
    Envía una imagen (file_obj: archivo abierto o InMemoryUploadedFile) al microservicio ArcFace
    y retorna una lista de resultados con IDs de estudiantes reconocidos y su similitud.
    """
    files = {'file': (file_obj.name, file_obj, file_obj.content_type)}
    try:
        response = requests.post(endpoint, files=files, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"[ArcFace] Error al conectar con el microservicio: {e}")
        return {"ok": False, "error": str(e)}

    try:
        data = response.json()
    except Exception as e:
        print(f"[ArcFace] Error al parsear JSON: {e}")
        return {"ok": False, "error": "Respuesta inválida del microservicio"}

    return data