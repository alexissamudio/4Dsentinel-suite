# Tarea: enviar los reportes diarios por email

Hoy los reportes en PDF se descargan a mano desde el dashboard.
Queremos automatizarlo.

Objetivo:
- Un job programado corre cada noche a medianoche.
- Genera el reporte PDF de cada usuario activo.
- Envia el PDF adjunto por email al usuario.

Alcance:
- Reusar el generador de PDF que ya existe.
- Solo usuarios activos (los inactivos se ignoran).
- Programar el job con el cron del sistema.
