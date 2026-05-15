from flask import Flask, request, jsonify
from datetime import datetime
import os
import json
import psycopg2
from openai import OpenAI

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def crear_tabla():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lecturas (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            temperatura FLOAT,
            humedad FLOAT,
            gas INTEGER,
            puerta INTEGER,
            tiempo_puerta INTEGER,
            aperturas INTEGER,
            estado VARCHAR(50),
            recomendacion TEXT
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


def guardar_lectura(data, estado, recomendacion):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO lecturas
        (temperatura, humedad, gas, puerta, tiempo_puerta, aperturas, estado, recomendacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """, (
        data["temperatura"],
        data["humedad"],
        data["gas"],
        data["puerta"],
        data["tiempo_puerta"],
        data["aperturas"],
        estado,
        recomendacion
    ))

    conn.commit()
    cur.close()
    conn.close()


def obtener_historial(limit=20):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT temperatura, humedad, gas, puerta, tiempo_puerta, aperturas, fecha
        FROM lecturas
        ORDER BY fecha DESC
        LIMIT %s;
    """, (limit,))

    filas = cur.fetchall()
    cur.close()
    conn.close()

    historial = []
    for fila in filas:
        historial.append({
            "temperatura": fila[0],
            "humedad": fila[1],
            "gas": fila[2],
            "puerta": fila[3],
            "tiempo_puerta": fila[4],
            "aperturas": fila[5],
            "fecha": str(fila[6])
        })

    return historial


def diagnostico_tecnico(data, historial):
    temp = float(data["temperatura"])
    hum = float(data["humedad"])
    gas = int(data["gas"])
    puerta = int(data["puerta"])
    tiempo_puerta = int(data["tiempo_puerta"])
    aperturas = int(data["aperturas"])

    riesgos = []
    estado = "normal"

    if temp > 8:
        riesgos.append("temperatura elevada")
        estado = "alerta"

    if hum > 60:
        riesgos.append("humedad alta")
        estado = "alerta"

    if gas > 400:
        riesgos.append("calidad de aire deficiente")
        estado = "alerta"

    if puerta == 1 and tiempo_puerta >= 10:
        riesgos.append("puerta abierta por tiempo prolongado")
        estado = "alerta"

    if aperturas >= 10:
        riesgos.append("frecuencia alta de aperturas")
        if estado != "alerta":
            estado = "advertencia"

    resumen = {
        "estado": estado,
        "riesgos": riesgos,
        "lecturas_actuales": data,
        "historial_reciente": historial
    }

    return resumen


def generar_recomendacion_con_openai(resumen):
    if client is None:
        return "No hay API Key de OpenAI configurada. El sistema detectó el estado, pero no pudo generar recomendación avanzada."

    prompt = f"""
Eres un asistente técnico para un sistema IoT llamado Smart Fridge Monitor.

Analiza las lecturas de un refrigerador y genera una recomendación profesional, clara y útil para el usuario.

No inventes datos.
No digas que puedes reparar el equipo.
Explica el posible impacto en conservación de alimentos y consumo energético.
Usa máximo 3 oraciones.
Debe sonar como una IA inteligente, no como una regla simple.

Datos:
{json.dumps(resumen, ensure_ascii=False)}
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt
    )

    return response.output_text.strip()


@app.route("/")
def home():
    return jsonify({
        "mensaje": "Servidor IA Smart Fridge funcionando correctamente",
        "base_datos": "PostgreSQL en la nube",
        "ia": "OpenAI API"
    })


@app.route("/analizar", methods=["POST"])
def analizar():
    try:
        data = request.json

        lectura = {
            "temperatura": float(data.get("temperatura", 0)),
            "humedad": float(data.get("humedad", 0)),
            "gas": int(data.get("gas", 0)),
            "puerta": int(data.get("puerta", 0)),
            "tiempo_puerta": int(data.get("tiempo_puerta", 0)),
            "aperturas": int(data.get("aperturas", 0))
        }

        historial = obtener_historial()
        resumen = diagnostico_tecnico(lectura, historial)
        recomendacion = generar_recomendacion_con_openai(resumen)

        guardar_lectura(
            lectura,
            resumen["estado"],
            recomendacion
        )

        return jsonify({
            "estado": resumen["estado"],
            "riesgos": resumen["riesgos"],
            "recomendacion": recomendacion
        })

    except Exception as e:
        return jsonify({
            "estado": "error",
            "recomendacion": "No se pudo analizar la lectura.",
            "detalle": str(e)
        }), 500


@app.route("/historial", methods=["GET"])
def historial():
    try:
        datos = obtener_historial(50)
        return jsonify(datos)
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if DATABASE_URL:
    crear_tabla()

if __name__ == "__main__":
    app.run(debug=True)
