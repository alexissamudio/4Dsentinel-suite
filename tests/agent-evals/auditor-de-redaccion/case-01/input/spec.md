# Spec: Modulo de notificaciones

## 1. Alcance
El modulo envia notificaciones a los usuarios cuando ocurre un evento relevante.
Cubre email y push. El canal SMS queda explicitamente fuera de alcance.

## 2. Requisitos funcionales
- RF-1: El sistema debe entregar las notificaciones de forma rapida.
- RF-2: Cada notificacion registra fecha, canal y destinatario.
- RF-3: El usuario puede desactivar las notificaciones push desde su perfil.
- RF-4: Si un envio falla, la notificacion se reintenta.

## 3. Requisitos no funcionales
- RNF-1: El sistema soporta el volumen de notificaciones esperado sin degradarse.
- RNF-2: La latencia de entrega push no supera los 5 segundos en el p95.

## 4. Canales soportados
El modulo soporta email, push y SMS para todos los eventos criticos.

## 5. Reintentos
Ante un fallo, el sistema reintenta hasta agotar los intentos configurados.

## 6. Criterios de aceptacion
- CA-1: Dado un evento, se genera una notificacion en cada canal habilitado.
- CA-2: La latencia p95 de push se mide en el panel de observabilidad.
