from flask import Flask, request, jsonify
import os
import json
import psycopg2
import google.generativeai as genai

app = Flask(__name__)

# Variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)
modelo_gemini = genai.GenerativeModel(GEMINI_MODEL)


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
            riesgos TEXT,
            recomendacion TEXT
        );
    """)

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

    if not riesgos:
        riesgos.append("condiciones normales")

    return {
        "estado": estado,
        "riesgos": riesgos,
        "lectura_actual": data,
        "historial_reciente": historial
    }


def generar_recomendacion_ia(resumen):
    if not GEMINI_API_KEY:
        return "No hay API Key de Gemini configurada. El sistema realizó el diagnóstico técnico, pero no pudo generar una recomendación avanzada."

    prompt = f"""
Eres un asistente inteligente especializado en monitoreo IoT de refrigeradores.

Tu tarea es analizar las lecturas del sistema Smart Fridge Monitor y generar una recomendación profesional para el usuario.

Debes tomar en cuenta:
- Temperatura
- Humedad
- Calidad del aire
- Estado de la puerta
- Tiempo de apertura
- Frecuencia de aperturas
- Historial reciente

Reglas de redacción:
- No inventes datos.
- No digas que puedes reparar el refrigerador.
- Explica el posible impacto en conservación de alimentos.
- Explica el posible impacto en consumo energético.
- Usa lenguaje natural, profesional y claro.
- Máximo 3 oraciones.
- La respuesta debe parecer escrita por una IA inteligente, no por una regla simple.

Datos del sistema:
{json.dumps(resumen, ensure_ascii=False)}
"""

    respuesta = modelo_gemini.generate_content(prompt)

    return respuesta.text.strip()


def guardar_lectura(data, estado, riesgos, recomendacion):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO lecturas
        (temperatura, humedad, gas, puerta, tiempo_puerta, aperturas, estado, riesgos, recomendacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (
        data["temperatura"],
        data["humedad"],
        data["gas"],
        data["puerta"],
        data["tiempo_puerta"],
        data["aperturas"],
        estado,
        ", ".join(riesgos),
        recomendacion
    ))

    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
def home():
    return jsonify({
        "mensaje": "Servidor IA Smart Fridge funcionando correctamente",
        "base_datos": "PostgreSQL en la nube",
        "ia": "Gemini API",
        "modelo": GEMINI_MODEL
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

        historial = obtener_historial(20)
        resumen = diagnostico_tecnico(lectura, historial)
        recomendacion = generar_recomendacion_ia(resumen)

        guardar_lectura(
            lectura,
            resumen["estado"],
            resumen["riesgos"],
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
