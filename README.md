# Plataforma de Tracking de Eventos de Usuarios

## Descripción general

Este proyecto implementa una plataforma de tracking de eventos diseñada para capturar interacciones de usuarios desde aplicaciones web y móviles.

El sistema recibe eventos a través de un endpoint HTTP, los valida y enriquece, y los persiste de forma durable en un formato adecuado para su posterior consumo por equipos de datos.

La solución está construida utilizando servicios gestionados de AWS y Terraform como infraestructura como código.

---

## Arquitectura

Flujo general:

```
Cliente (Web/Mobile)
│
▼
API Gateway (HTTP API)
│
▼
Lambda (Recepción, validación, procesamiento)
│
├── Éxito → Kinesis Firehose → S3 (GZIP, particionado)
├── Error → SQS (DLQ)
└── Logs → CloudWatch
```

---

## Componentes principales

### API Gateway

- Expone un endpoint HTTP (`POST /events`)
- Recibe eventos desde clientes

### Lambda (Python)

- Valida eventos entrantes
- Enriquece eventos (event_id, received_at)
- Envía eventos válidos a Firehose
- Envía eventos fallidos a SQS (DLQ)
- Genera logs estructurados

### Kinesis Firehose

- Agrupa y bufferiza eventos
- Comprime datos (GZIP)
- Entrega eventos a S3

### S3

- Almacena eventos en estructura particionada por fecha
- Permite consumo por equipos de datos
- Encriptación habilitada

### SQS (DLQ)

- Almacena eventos que fallaron en la recepción
- Permite análisis o reprocesamiento posterior

---

## Requisitos funcionales

- Recibir eventos desde aplicaciones cliente
- Persistir todos los eventos válidos de forma durable
- Permitir que los datos sean consumibles por equipos de datos

---

## Requisitos no funcionales

### Alta disponibilidad

- Arquitectura serverless
- Sin puntos únicos de falla

### Escalabilidad

- API Gateway y Lambda escalan automáticamente
- Firehose maneja picos de tráfico
- S3 soporta almacenamiento prácticamente ilimitado

### Seguridad

- Validación mediante API key
- IAM con principio de menor privilegio
- Encriptación en S3
- Comunicación vía HTTPS

### Costos

- Modelo pay-per-use
- Compresión GZIP reduce almacenamiento
- Sin infraestructura siempre activa

---

## Estimación de costos

Suposiciones:

- 1,000,000 eventos por día
- ~1.5 KB por evento (~1.5 GB/día)

Componentes principales:

- Lambda: costo bajo por ejecución (pay-per-use)
- API Gateway: costo por request
- Firehose: costo por volumen de datos procesados
- S3: almacenamiento (~45 GB/mes)

Optimización:

- Uso de compresión GZIP reduce costos de almacenamiento
- Arquitectura serverless evita costos fijos

Estimación:
El costo mensual es bajo y escala linealmente con el volumen de eventos.

---

## Formato de evento

Ejemplo:

```json
{
  "event_type": "sign_in",
  "user_id": "user_123",
  "timestamp": "2026-04-29T21:00:00Z",
  "source": "web",
  "schema_version": "1.0",
  "properties": {
    "device": "desktop",
    "browser": "chrome"
  }
}
```

---

## Cómo desplegar

### Prerequisitos

- AWS CLI configurado (`aws configure`)
- Terraform instalado

---

## Estrategia de despliegue

Para este proyecto se eligió la opción (A): despliegue real en AWS.

Esto permite validar el sistema end-to-end, incluyendo:

- Recepción de eventos
- Persistencia en S3
- Manejo de errores con DLQ
- Observabilidad mediante CloudWatch

El despliegue se realizó utilizando Terraform con estado remoto en S3.

---

### Pasos

```bash
cd infra
terraform init
terraform plan
terraform apply
```

---

### Outputs importantes

Al finalizar, Terraform mostrará valores como:

- `api_endpoint`
- `events_bucket_name`
- `failed_events_dlq_url`

La API key se define en el archivo `terraform.tfvars`.

Estos valores son necesarios para interactuar con el sistema y realizar pruebas.

---

### Destruir infraestructura (opcional)

```bash
terraform destroy
```

---

## Cómo enviar un evento de prueba

```bash
curl -X POST "https://<api-endpoint>/dev/events" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: <api-key>" \
  -d '{
    "event_type": "sign_in",
    "user_id": "user_123",
    "timestamp": "2026-04-29T21:00:00Z",
    "source": "web",
    "schema_version": "1.0",
    "properties": {
      "device": "desktop"
    }
  }'
```

---

## Cómo consultar los datos

### Listar archivos en S3

```bash
aws s3 ls s3://<bucket-name> --recursive
```

### Descargar y visualizar

```bash
aws s3 cp s3://<bucket-name>/<path>.gz .
gzip -dc <file>.gz
```

Los eventos se almacenan como JSON separados por línea.

### Validación

Para verificar que el flujo funciona correctamente:

1. Enviar un evento con curl
2. Esperar unos segundos (buffer de Firehose)
3. Consultar S3 y verificar que el archivo contiene el evento enviado

---

## Manejo de errores

- Errores de validación → HTTP 400
- Requests no autorizados → HTTP 401
- Fallos en Firehose → enviados a SQS (DLQ)
- Logs estructurados en CloudWatch

---

## Observabilidad

- CloudWatch Logs para ejecución de Lambda
- Logs en formato JSON
- DLQ permite inspección de fallos

---

## Operación y monitoreo

En caso de fallos:

- Errores en la recepción quedan registrados en CloudWatch Logs
- La DLQ permite inspección y reprocesamiento de eventos fallidos

Escenario típico:
Si Firehose falla, los eventos no se pierden y quedan disponibles en la DLQ para análisis posterior.

---

## CI/CD

Se implementó un pipeline con GitHub Actions que:

- Ejecuta `terraform fmt -check`
- Ejecuta `terraform validate`
- Ejecuta `terraform plan`
- Usa GitHub Secrets para credenciales

---

## Decisiones y trade-offs

### Arquitectura serverless

Elegida por simplicidad y escalabilidad.

**Alternativa:**  
ECS/EKS descartado por mayor complejidad operativa.

---

### Firehose vs Kinesis Streams

Firehose elegido por ser totalmente gestionado.

**Trade-off:**  
Menor control en tiempo real.

---

### API key

Se utilizó API Key como mecanismo simple de autenticación para este caso.

**Trade-off:**  
No cubre escenarios avanzados de autenticación/autorización.

---

### Remote state

Configurado en S3 para compartir estado entre local y CI.

---

## Prueba de DLQ

Se implementó un mecanismo controlado de fallo:

```
X-Force-Firehose-Error: true
```

Permite validar el flujo hacia la DLQ sin depender de fallos reales.

---

## Mejoras futuras

- Autenticación robusta (Cognito/OAuth)
- Gestión de esquemas de eventos
- Reprocesamiento automático desde DLQ
- Alertas basadas en métricas (CloudWatch)
