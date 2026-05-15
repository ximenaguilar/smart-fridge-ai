from flask import Flask, request, jsonify
import os
import json
import psycopg2
from openai import OpenAI

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


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


def generar_recomendacion_groq(resumen):
    prompt = f"""
Eres un asistente técnico especializado en sistemas IoT de refrigeración.

Analiza las lecturas del proyecto Smart Fridge Monitor y genera una recomendación profesional para el usuario.

Toma en cuenta:
- Temperatura
- Humedad
- Calidad del aire
- Estado de puerta
- Tiempo de apertura
- Frecuencia de apertura
- Historial reciente

Reglas:
- No inventes datos.
- No digas que puedes reparar el refrigerador.
- Explica posible impacto en conservación de alimentos.
- Explica posible impacto en consumo energético.
- Máximo 3 oraciones.
- Responde en español.
- Debe sonar como una IA profesional, no como un simple if.

Datos:
{json.dumps(resumen, ensure_ascii=False)}
"""

    respuesta = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Eres una IA técnica para análisis IoT de refrigeradores."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4,
        max_tokens=180
    )

    return respuesta.choices[0].message.content.strip()


def recomendacion_respaldo(resumen):
    estado = resumen["estado"]
    riesgos = resumen["riesgos"]

    if estado == "normal":
        return "El refrigerador opera dentro de condiciones estables. No se detectan riesgos inmediatos para la conservación de alimentos ni señales de uso energético ineficiente."

    texto = "Se detectaron condiciones anómalas: " + ", ".join(riesgos) + ". "

    if "temperatura elevada" in riesgos:
        texto += "La temperatura elevada puede afectar la conservación de alimentos y obligar al sistema a trabajar más para recuperar el frío. "

    if "humedad alta" in riesgos:
        texto += "La humedad alta puede favorecer condensación interna y deterioro más rápido de productos sensibles. "

    if "calidad de aire deficiente" in riesgos:
        texto += "La calidad de aire deficiente puede indicar presencia de gases o alimentos en posible deterioro. "

    if "puerta abierta por tiempo prolongado" in riesgos or "frecuencia alta de aperturas" in riesgos:
        texto += "El patrón de apertura puede incrementar la pérdida de frío y elevar el consumo energético."

    return texto.strip()


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
        "ia": "Groq API",
        "modelo": GROQ_MODEL
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

        try:
            recomendacion = generar_recomendacion_groq(resumen)
            fuente_ia = "groq"
        except Exception:
            recomendacion = recomendacion_respaldo(resumen)
            fuente_ia = "motor_local_respaldo"

        guardar_lectura(
            lectura,
            resumen["estado"],
            resumen["riesgos"],
            recomendacion
        )

        return jsonify({
            "estado": resumen["estado"],
            "riesgos": resumen["riesgos"],
            "fuente_ia": fuente_ia,
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
