"""# Contexto y Arquitectura: Módulo POS Kosto

## 1. Estrategia de Ramas y Despliegue
* **Rama Principal de Desarrollo:** `feature/pos-core`
* **Regla de Fusión:** Cero integraciones a `main` sin validación de tipado estricto, análisis de seguridad estático y pruebas de integración superadas al 100%.
* **Empaquetado:** Totalmente compatible con la acción de GitHub Actions actual para generar el binario ejecutable (`.exe`) de Windows de forma automatizada mediante `uv`.

## 2. Postura de Seguridad (Zero Trust) y Auditoría
* **Gestión de Dependencias:** Uso estricto y exclusivo de `uv.lock`. Queda estrictamente prohibida la instalación de paquetes de terceros que no pasen la validación de hash criptográfico y la verificación de la integridad de la cadena de suministro.
* **Prevención de Inyecciones (SQLi):** Cero tolerancia al uso de f-strings, formateo o concatenación manual de cadenas en sentencias SQL. Es obligatorio el uso de consultas parametrizadas para cualquier interacción con la base de datos SQLite.
* **Sanitización Dinámica:** Todo input proveniente de periféricos externos (teclado, lector de códigos de barras, pantallas táctiles) debe ser validado por tipo de dato, formato y longitud máxima en la capa de presentación antes de ser transmitido a las capas internas.
* **Registro de Auditoría (Audit Trail):** Operaciones críticas y sensibles dentro del negocio (anulaciones de tickets, modificaciones manuales de precios, aplicación de descuentos especiales o cierres de caja) deben registrarse obligatoriamente en una tabla persistente de auditoría (`Logs_Auditoria`), almacenando marca de tiempo exacta, identificador de la sesión del cajero y el estado anterior/nuevo del registro.

## 3. Arquitectura Limpia Estricta (Clean Architecture)
El módulo se desacopla en cuatro capas independientes y unidireccionales para garantizar el mantenimiento a largo plazo y la reutilización del código:
1. **Capa de Presentación (UI):** Responsable exclusiva del renderizado visual y de capturar los eventos físicos del usuario. No contiene reglas comerciales ni procesamiento de datos.
2. **Capa de Casos de Uso (Lógica de Negocio):** Centraliza las reglas operativas como el cálculo exacto de impuestos, validación de existencias en tiempo real y el cálculo del vuelto/cambio. Es completamente agnóstica a la base de datos y al hardware.
3. **Capa de Datos (Repositorios):** Abstracción directa sobre la base de datos SQLite encargada únicamente de la persistencia de las entidades `Ventas`, `Detalles_Venta` y los registros de auditoría.
4. **Capa de Infraestructura y Hardware:** Módulo completamente aislado que encapsula la comunicación con la impresora térmica (vía protocolos ESC/POS o APIs nativas de Windows). Ninguna otra capa interna debe conocer el puerto físico, el estado de conexión o el ancho del papel de impresión (58mm/80mm).

## 4. Robustez de Datos (Transacciones ACID)
* **Integridad Transaccional:** El registro completo de una venta y la correspondiente deducción física del inventario deben ejecutarse estrictamente dentro de un bloque de transacción atómica (`BEGIN TRANSACTION` y `COMMIT`).
* **Estrategia ante Fallos:** Si el guardado del ticket falla o la actualización del stock físico arroja un error imprevisto, se debe invocar inmediatamente un `ROLLBACK`. El estado de la base de datos jamás debe quedar en un punto intermedio de inconsistencia.

## 5. Estándares de Código y Resiliencia de Hardware
* **Tipado Estático:** Uso mandatorio de *Type Hints* en la definición de cada función, método y clase dentro del módulo POS, permitiendo auditorías de código estáticas rigurosas.
* **Nomenclatura Semántica:** Nombres de funciones explícitos y descriptivos orientados al dominio del negocio (ej. `procesar_pago_efectivo()`, `deducir_inventario_por_venta()`). Se prohíben abreviaturas crípticas o ambiguas.
* **Resiliencia ante Fallos de Hardware:** Las excepciones de comunicación con la impresora térmica (ausencia de papel, atasco físico, cable USB desconectado o bloqueo de cola de impresión en Windows) deben ser capturadas de manera específica en la capa de Infraestructura. **Estos fallos físicos bajo ninguna circunstancia deben colgar o congelar la aplicación principal**. El sistema confirmará la venta en la base de datos y ofrecerá al cajero un aviso visual no bloqueante con la opción de "Reintentar Impresión" una vez que el problema del hardware sea subsanado.
"""
