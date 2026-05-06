# Stress test Damian

Scripts simples para analizar como responde la API bajo carga concurrente, registrando requests, latencias, errores y consumo basico.

## Prerrequisitos

Levantar la app:

```bash
docker compose up --build
```

Validar que responde:

```bash
curl http://localhost:8000/health
```

## Ejecutar stress test basico

```bash
uv run python stress_test_damian/stress_api.py \
  --base-url http://localhost:8000 \
  --duration 30 \
  --concurrency 20
```

El script imprime un resumen:

```text
Stress test summary
requests_total=1234
requests_failed=0
status_codes={'200': 900, '201': 334}
latency_avg_ms=12.34
latency_p95_ms=45.67
latency_p99_ms=90.12
latency_max_ms=123.45
```

Y genera CSVs en:

```text
stress_test_damian/results/
```

Archivos generados:

- `requests_YYYYMMDD_HHMMSS.csv`: una fila por request, con metodo, path, status, latencia y error.
- `resources_YYYYMMDD_HHMMSS.csv`: muestras periodicas de consumo.

El CSV de requests tambien incluye el `payload` enviado. Esto sirve para reproducir requests que devuelven `500`, `422` o timeouts.

## Medir consumo por contenedor Docker

Primero identificar el nombre del contenedor:

```bash
docker compose ps
```

Ejecutar pasando el contenedor de la API:

```bash
uv run python stress_test_damian/stress_api.py \
  --base-url http://localhost:8000 \
  --duration 60 \
  --concurrency 50 \
  --docker-container alertas_climaticas_bot-api-1
```

Si el nombre del contenedor es distinto, reemplazar `alertas_climaticas_bot-api-1`.

## Medir consumo por PID

Si la app corre local sin Docker, buscar el PID:

```bash
ps -axo pid,command | grep "uvicorn app.main:app"
```

Ejecutar:

```bash
uv run python stress_test_damian/stress_api.py \
  --base-url http://localhost:8000 \
  --duration 60 \
  --concurrency 50 \
  --pid 12345
```

## Que trafico genera

El script mezcla requests:

- `POST /weather-events`: crea eventos climaticos.
- `POST /weather-events` repetidos: prueba idempotencia ante duplicados.
- `POST /alerts`: crea reglas de alerta.
- `POST /alerts/evaluate`: fuerza evaluacion manual.
- `GET /notifications`: consulta notificaciones.
- `GET /health`: valida disponibilidad.

El resumen final separa resultados por status y endpoint:

```text
endpoint_status={'POST /weather-events 201': 68, 'POST /alerts 500': 27}
```

Esto permite detectar rapido que operacion se degrada bajo concurrencia.

Parametro util:

```bash
--duplicate-ratio 0.5
```

Hace que el 50% de los `POST /weather-events` intenten repetir el mismo evento. Sirve para validar que la API no bloquee por `UniqueViolationError`.

## Ejemplos de carga

Carga moderada:

```bash
uv run python stress_test_damian/stress_api.py --duration 30 --concurrency 20
```

Carga alta:

```bash
uv run python stress_test_damian/stress_api.py --duration 120 --concurrency 100 --duplicate-ratio 0.4
```

Prueba enfocada en concurrencia de duplicados:

```bash
uv run python stress_test_damian/stress_api.py --duration 60 --concurrency 80 --duplicate-ratio 0.9
```
