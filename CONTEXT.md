Actúa como un Ingeniero de Software Senior experto en Python 3.12 y Clean Architecture. Tu tarea es escribir el código completo para un sistema de control de inventario de escritorio, diseñado para funcionar 100% offline en Windows 10 Pro.

RESTRICCIONES Y REQUISITOS DE CALIDAD:
1. Cero alucinaciones: Usa únicamente librerías estándar de Python y `customtkinter`. No inventes módulos que no existen.
2. Seguridad (Zero Trust): El código debe estar blindado contra inyecciones SQL usando consultas parametrizadas en SQLite. Las dependencias se instalarán mediante `uv` con políticas estrictas (ej. `ignore-scripts=true`), por lo que el código no debe depender de binarios de terceros inseguros o descargas en tiempo de ejecución.
3. Principios SOLID y DRY: El código debe ser altamente reutilizable. Ningún bloque de lógica de cálculo o de base de datos debe estar acoplado a la interfaz gráfica.
4. Modularidad: Divide estrictamente el proyecto en las siguientes capas (proporciona el código en bloques separados por archivo):
   - `domain/models.py`: Lógica pura de cálculo de precios.
   - `infrastructure/database.py`: Conexión y operaciones con SQLite3.
   - `presentation/gui.py`: Interfaz con CustomTkinter.
   - `main.py`: Punto de entrada que orquesta las dependencias.

LÓGICA DEL NEGOCIO (Dominio):
El sistema recibe un lote de productos y debe calcular automáticamente los valores unitarios.
- Entradas: Nombre del producto, Costo total del paquete (ej. $3.67), Unidades por paquete (ej. 12).
- Cálculos requeridos en memoria:
  * Costo unitario real (ej. 3.67 / 12 = 0.3058)
  * Precio de venta sugerido (redondeado, ej. 0.31)
- Modificación de usuario: El usuario puede sobreescribir el precio de venta sugerido e ingresar uno manual (ej. 0.35).
- Cálculo final: Ganancia neta por unidad (Precio manual - Costo unitario real).

INTERFAZ GRÁFICA (Presentación):
Usa `customtkinter`. La interfaz debe ser minimalista, de una sola ventana dividida en dos secciones (formulario de ingreso a la izquierda, tabla de visualización/búsqueda a la derecha). 
Aplica estrictamente esta paleta de colores (basada en el tema Catppuccin Mocha):
- Fondo principal: "#1e1e2e"
- Cajas de texto y tablas: "#181825"
- Texto principal: "#cdd6f4"
- Botones de acción: "#89b4fa"
- Indicadores de éxito/ganancia: "#a6e3a1"

BASE DE DATOS (Infraestructura):
Usa `sqlite3` nativo. Crea una tabla `productos` con los campos necesarios para almacenar todos los valores mencionados (costos, precios y ganancias). Implementa funciones limpias para inicializar la base de datos, insertar un nuevo registro, actualizar un registro existente y obtener todos los registros.

ENTREGABLE ESPERADO:
Proporciona únicamente el código fuente de los archivos requeridos, comentados profesionalmente donde sea necesario, listos para ser guardados en sus respectivos directorios y ejecutados/empaquetados.
