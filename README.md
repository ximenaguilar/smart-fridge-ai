# Smart Fridge AI Server

Sistema de inteligencia artificial para el proyecto Smart Fridge Monitor.

## Descripción

Este servidor recibe datos enviados desde un ESP32 conectado a sensores ambientales dentro de un refrigerador inteligente.

Los datos son analizados mediante lógica de inteligencia artificial básica para:

- Detectar anomalías
- Identificar patrones de uso
- Generar recomendaciones
- Detectar posibles riesgos de deterioro
- Optimizar consumo energético

El sistema trabaja junto con:

- ESP32
- DHT22
- MQ-135
- Reed Switch
- Blynk IoT
- Flask
- Python
- Render Cloud

---

# Variables monitoreadas

- Temperatura
- Humedad
- Calidad del aire
- Estado de puerta
- Tiempo de apertura
- Frecuencia de apertura

---

# Tecnologías utilizadas

- Python
- Flask
- Pandas
- Scikit-Learn
- ESP32
- Blynk IoT
- Render Cloud

---

# Estructura del proyecto

smart-fridge-ai/
│
├── app.py
├── requirements.txt
├── modelo_ia.py
├── datos.csv
└── README.md

---

# Instalación local

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar servidor:

```bash
python app.py
```

---

# Endpoint principal

POST:

```bash
/analizar
```

Ejemplo JSON enviado por el ESP32:

```json
{
  "temperatura": 7.5,
  "humedad": 62,
  "gas": 450,
  "puerta": 1,
  "tiempo_puerta": 12,
  "aperturas": 8
}
```

---

# Respuesta del servidor

```json
{
  "estado": "alerta",
  "recomendacion": "La temperatura está elevada. Revise si la puerta quedó abierta."
}
```

---

# Objetivo del proyecto

Desarrollar un sistema IoT inteligente capaz de monitorear las condiciones internas de un refrigerador y generar recomendaciones automáticas orientadas a mejorar la conservación de alimentos y optimizar el consumo energético.

---

# Autor

Proyecto universitario desarrollado para Arquitectura de Computadoras I.