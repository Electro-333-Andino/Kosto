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

Actúa como un Desarrollador Senior de Software experto en Python, CustomTkinter y arquitectura de bases de datos relacionales (SQLite/SQLAlchemy). Necesitas refactorizar una aplicación de inventario y punto de venta (POS) de escritorio para Windows.

Entorno de Ejecución:
El sistema operará en una PC/Servidor con Windows 10 aislada (sin conexión a internet). El código debe ser altamente escalable (utilizando el patrón MVC: Modelo-Vista-Controlador) y prepararse para una compilación con PyInstaller.

Requerimientos de Refactorización:

1. Gestión de Rutas y Cumplimiento del Estándar Windows (Separación de Datos):

Modifica el gestor de rutas del código. El ejecutable final residirá en C:\Program Files\Kosto (entorno de solo lectura).

La base de datos SQLite (.db) y los logs deben ubicarse obligatoriamente en C:\ProgramData\Kosto (o os.environ.get('PROGRAMDATA')).

Implementa una clase de inicialización que verifique si la estructura de carpetas en ProgramData existe al arrancar. Si no existe, el código de Python debe crearla automáticamente antes de intentar conectar a la base de datos.

2. Seguridad y Manejo de la Base de Datos:

Implementa todas las consultas utilizando sentencias parametrizadas o un ORM (como SQLAlchemy) para garantizar seguridad y facilitar una futura migración.

El código debe capturar excepciones (sqlite3.OperationalError o equivalentes del ORM) para manejar correctamente los bloqueos si Windows restringe los permisos de escritura/eliminación del archivo físico. Mostrar mensajes de error limpios en la UI en lugar de crashear.

Asegura el cierre correcto de las conexiones a la base de datos (uso de context managers with) para evitar corrupción de datos en apagados repentinos.

3. Corrección de Bug en UI (Botones Invisibles):

Refactoriza las clases de las vistas de CustomTkinter. Actualmente, los botones de "Guardar", "Editar" y "Eliminar" productos se instancian pero no son visibles en pantalla.

Aplica las siguientes correcciones en la vista:

Asegura que el parámetro master de los botones apunte al CTkFrame correcto y visible.

Verifica que los métodos de renderizado (.grid(), .pack() o .place()) se estén llamando correctamente sobre las instancias de los botones.

Corrige cualquier problema de superposición (Z-index), asegurando que ningún CTkFrame contenedor se dibuje encima de los botones.

Asegura que las funciones de acción pasadas a command= no tengan paréntesis para no bloquear la carga del widget.

4. Restricciones Offline y Diseño Escalable:

Garantiza que no existan llamadas a APIs externas, descargas de fuentes o dependencias que requieran red.

Separa estrictamente la lógica de la interfaz (Views), las consultas a la base de datos (Models) y el manejo de eventos (Controllers).

Prepara las referencias de imágenes, íconos y fuentes utilizando una función de resolución de rutas relativas (sys._MEIPASS) para que funcionen correctamente tras compilar.

Por favor, entrégame el código de los módulos refactorizados (models.py, views.py, controllers.py y main.py) aplicando estas directrices.
