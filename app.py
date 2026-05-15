from flask import Flask, request, jsonify
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)

DATA_FILE = "datos.csv"

def guardar_datos(data):
    nuevo = {
        "fecha": datetime.now().isoformat(),
        "temperatura": data.get("temperatura"),
        "humedad": data.get("humedad"),
        "gas": data.get("gas"),
        "puerta": data.get("puerta"),
        "tiempo_puerta": data.get("tiempo_puerta"),
        "aperturas": data.get("aperturas")
    }

    df_nuevo = pd.DataFrame([nuevo])

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, df_nuevo], ignore_index=True)
    else:
        df = df_nuevo

    df.to_csv(DATA_FILE, index=False)


def analizar_ia(data):
    temp = float(data.get("temperatura", 0))
    hum = float(data.get("humedad", 0))
    gas = int(data.get("gas", 0))
    tiempo_puerta = int(data.get("tiempo_puerta", 0))
    aperturas = int(data.get("aperturas", 0))

    recomendaciones = []
    estado = "normal"

    if temp > 8:
        estado = "alerta"
        recomendaciones.append("La temperatura está elevada. Revise si la puerta quedó abierta o si el refrigerador tiene exceso de carga.")

    if hum > 60:
        estado = "alerta"
        recomendaciones.append("La humedad está alta. Verifique empaques abiertos o exceso de humedad interna.")

    if gas > 400:
        estado = "alerta"
        recomendaciones.append("La calidad del aire es baja. Revise si hay alimentos en descomposición.")

    if tiempo_puerta > 10:
        estado = "alerta"
        recomendaciones.append("La puerta permaneció abierta demasiado tiempo. Esto puede aumentar el consumo energético.")

    if aperturas > 10:
        estado = "advertencia"
        recomendaciones.append("Se detectó uso frecuente del refrigerador. Se recomienda agrupar las aperturas para reducir pérdida de frío.")

    if not recomendaciones:
        recomendaciones.append("El refrigerador opera dentro de condiciones normales.")

    return {
        "estado": estado,
        "recomendacion": " ".join(recomendaciones)
    }


@app.route("/")
def home():
    return jsonify({
        "mensaje": "Servidor IA Smart Fridge funcionando correctamente"
    })


@app.route("/analizar", methods=["POST"])
def analizar():
    data = request.json

    guardar_datos(data)
    resultado = analizar_ia(data)

    return jsonify(resultado)


if __name__ == "__main__":
    app.run(debug=True)