# Sistema de Alertas Climaticas

API FastAPI para configurar alertas climaticas por campo agricola y generar notificaciones cuando los datos meteorologicos almacenados superan los umbrales definidos.

## Stack

- FastAPI
- SQLAlchemy 2 async
- PostgreSQL
- Alembic
- Docker Compose
- uv
- Pytest

## Correr con Docker

```bash
docker compose up -d --build
```

El servicio queda disponible en:

- API: <http://localhost:8000>
- OpenAPI: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`

El contenedor de la API instala dependencias con `uv sync --frozen --no-dev` y ejecuta `uv run --no-dev alembic upgrade head` antes de iniciar Uvicorn. Las migraciones crean el esquema y cargan datos mock de usuarios, campos, reglas y eventos climaticos futuros.

## Endpoints principales

- `GET /health`
- `GET /health/db`
- `GET /users`
- `GET /fields`
- `GET /weather-events`
- `POST /weather-events`
- `GET /alerts`
- `POST /alerts`
- `PATCH /alerts/{alert_rule_id}`
- `POST /alerts/evaluate`
- `GET /notifications`
- `POST /notifications/{notification_id}/read`

## Flujo dummy completo 

Este flujo prueba el sistema de punta a punta: usuarios, campos, configuracion de alertas, datos meteorologicos, evaluacion e idempotencia de notificaciones.

### 1. Levantar API y base de datos

```bash
docker compose up --build
```

Podemos hacer un log de docker para ver en el estado que esta nuestra API.
```bash
docker logs alertas_climaticas_bot-api-1
```
y
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```
Para conocer si esta saludable el servicio, si todo levanto OK, deberia respondernos

```json
{"status":"ok"}
```

El endpoint `/health/db` tambien ejecuta una consulta liviana contra la base y responde:

```json
{"status":"ok","database":"ok"}
```

### 2. Ver datos iniciales cargados por migracion

Las migraciones cargan dos productores, dos campos, dos reglas de alerta y eventos climaticos mock futuros(todos estos datos son ficticios).

```bash
curl http://localhost:8000/users
curl http://localhost:8000/fields
curl http://localhost:8000/alerts
curl http://localhost:8000/weather-events
```

IDs utiles del seed:

- Usuario norte: `11111111-1111-1111-1111-111111111111`
- Campo norte: `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`
- Usuario sur: `22222222-2222-2222-2222-222222222222`
- Campo sur: `bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb`

### 3. Crear una nueva regla de alerta

Este ejemplo configura una alerta de tormenta para el campo norte. El usuario quiere ser notificado cuando la probabilidad de `storm` sea mayor o igual a `30`.

```bash
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "11111111-1111-1111-1111-111111111111",
    "field_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "event_type": "storm",
    "threshold": 30,
    "active": true
  }'
```

Respuesta esperada: una regla con `event_type: "storm"`, `threshold: 30` y `active: true`.

### 4. Registrar un evento meteorologico que supera el umbral

Este evento representa una tormenta futura con probabilidad `80`, por encima del umbral `30`.

```bash
curl -X POST http://localhost:8000/weather-events \
  -H "Content-Type: application/json" \
  -d '{
    "field_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "event_date": "2099-01-01T12:00:00Z",
    "event_type": "storm",
    "probability": 80,
    "source": "manual_challenger_test"
  }'
```

Respuesta esperada: un evento meteorologico con `event_type: "storm"` y `probability: 80`.

`event_date` recibe un timestamp ISO 8601 con fecha y hora. Si se ejecuta el mismo `POST /weather-events` mas de una vez con igual `field_id`, `event_date` y `event_type`, la API devuelve el evento existente. Esto evita que el constraint unico bloquee el flujo de prueba cuando se repite un comando.

### 5. Ejecutar la evaluacion manualmente

El background job corre periodicamente, pero este endpoint permite probar la evaluacion sin esperar el intervalo.

Para verificar cuando corre el job automatico, mirar los logs de la API en otra terminal:

```bash
docker logs alertas_climaticas_bot-api-1 -f 
```

Cada ejecucion automatica registra mensajes como:

```text
automatic alert evaluation job started at 2026-05-06T14:36:16.500219+00:00
automatic alert evaluation job completed; created_notifications=1
automatic alert evaluation worker sleeping; next_run_in_seconds=60
```

```bash
curl -X POST http://localhost:8000/alerts/evaluate
```

Respuesta esperada si el background job todavia no proceso el evento:

```json
{"created_notifications":1}
```

Si tambien existen los datos mock sin evaluar, el numero puede ser mayor porque se crean todas las notificaciones pendientes que superan umbrales.

Si devuelve `{"created_notifications":0}`, revisar `/notifications`: puede significar que el background job ya corrio y creo la notificacion antes de la evaluacion manual. El endpoint es idempotente y solo informa cuantas notificaciones nuevas creo en esa ejecucion.

### 6. Consultar notificaciones generadas

```bash
curl http://localhost:8000/notifications
```
y podemos simular un pulling de eventos de esta manera

```bash
watch -n 1 curl -s http://localhost:8000/notifications
```
Tambien se pueden filtrar por usuario:

```bash
curl "http://localhost:8000/notifications?user_id=11111111-1111-1111-1111-111111111111"
```

En la respuesta deberia aparecer un mensaje similar a:

```text
Alerta climatica para Lote Maiz: storm con probabilidad 80% el 2099-01-01T12:00:00+00:00 supera el umbral 30%.
```

### 7. Probar idempotencia

Ejecutar la evaluacion de nuevo:

```bash
curl -X POST http://localhost:8000/alerts/evaluate
```

Respuesta esperada si no hay nuevos eventos pendientes:

```json
{"created_notifications":0}
```

Esto demuestra que el sistema no duplica notificaciones para la misma regla y el mismo evento climatico.

### 8. Caso negativo: evento por debajo del umbral

Crear un evento `hail` con probabilidad `20` y luego una alerta con umbral `70`.

```bash
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "22222222-2222-2222-2222-222222222222",
    "field_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "event_type": "hail",
    "threshold": 70,
    "active": true
  }'

curl -X POST http://localhost:8000/weather-events \
  -H "Content-Type: application/json" \
  -d '{
    "field_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "event_date": "2099-01-02T12:00:00Z",
    "event_type": "hail",
    "probability": 20,
    "source": "manual_challenger_test"
  }'

curl -X POST http://localhost:8000/alerts/evaluate
```

No deberia generarse una notificacion para ese evento, porque `20` no supera el umbral `70`.

### 9. Marcar una notificacion como leida

Tomar un `id` de la respuesta de `/notifications` y ejecutar:

```bash
curl -X POST http://localhost:8000/notifications/{notification_id}/read
```

Respuesta esperada: la notificacion queda con `status: "READ"` y `read_at` informado.

## Migraciones

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
```

Las migraciones incluidas son:

- `0001_create_alerting_schema.py`: tablas, indices, constraints y enums.
- `0002_seed_mock_weather_data.py`: datos iniciales mock para simular el job de ingesta meteorologica existente.
- `0003_weather_events_datetime.py`: convierte `event_date` a timestamp con timezone.

## Tests

```bash
uv sync
uv run pytest
```

Los tests validan la salud de la API y la evaluacion idempotente de alertas.
Tambien cubren validaciones de payload, ownership de campos, duplicados idempotentes, filtro de notificaciones por usuario y marcado de notificaciones como leidas.

## Decisiones tecnicas

- La aplicacion usa FastAPI con SQLAlchemy 2 async y `asyncpg` para que las operaciones de I/O contra PostgreSQL no bloqueen el event loop.
- El modelo separa `weather_events` de `alert_rules` y `notifications`. Esto mantiene la ingesta meteorologica desacoplada de la evaluacion de alertas.
- `notifications` tiene constraint unico por `alert_rule_id` y `weather_event_id`, evitando duplicados aunque el job corra varias veces.
- `weather_events` es idempotente por `field_id`, `event_date` y `event_type`: repetir el mismo evento devuelve el existente. `event_date` guarda fecha y hora, por lo que dos eventos del mismo tipo en el mismo campo pueden coexistir si ocurren en horarios distintos.
- `alert_rules` es idempotente por `user_id`, `field_id` y `event_type`: repetir la misma regla devuelve la existente.
- La evaluacion de alertas inserta notificaciones con `ON CONFLICT DO NOTHING` sobre el par regla/evento. Asi el endpoint manual y el background job pueden correr mas de una vez sin duplicar notificaciones.
- PostgreSQL sigue siendo la fuente de verdad con constraints unicos; los servicios capturan `IntegrityError`, hacen `rollback` y devuelven el registro existente cuando corresponde en altas idempotentes.
- Los errores de dominio usan una excepcion propia y un handler global de FastAPI para devolver `422` de forma consistente sin repetir `try/except` en cada endpoint.
- El job corre dentro del lifespan de FastAPI para el ejercicio. En produccion real lo moveria a un worker separado, manteniendo el mismo servicio `evaluate_alerts`.
- Las probabilidades y umbrales se validan con constraints de DB y Pydantic entre `0` y `100`.
- El endpoint `POST /alerts/evaluate` existe para operar y probar manualmente el job sin esperar el intervalo periodico.
- No se implementa integracion con WhatsApp porque el challenge indica que no hace falta; las notificaciones quedan persistidas y consultables por API.
