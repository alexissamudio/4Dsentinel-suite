# Requisito: Exportacion de reportes

## Historia
Como analista, quiero exportar un reporte de ventas para compartirlo con direccion.

## Detalle
El usuario selecciona un rango de fechas y el sistema genera un archivo descargable.
El archivo se entrega en el formato estandar de la empresa.
El reporte incluye todas las ventas del periodo seleccionado.
La exportacion debe completarse en un tiempo razonable.

## Permisos
Solo los usuarios autorizados pueden exportar reportes.

## Criterios de aceptacion
- CA-1: El archivo generado se puede abrir sin errores.
- CA-2: El total del reporte coincide con el total mostrado en pantalla.
- CA-3: El rango de fechas maximo permitido es de 12 meses.
