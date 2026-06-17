# Kosto — Sistema Profesional de Gestión de Inventario, Márgenes y Punto de Venta (POS)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-black.svg)](pyproject.toml)
[![Type Checker](https://img.shields.io/badge/type_checker-mypy-blue.svg)](pyproject.toml)

**Kosto** es una aplicación de escritorio profesional diseñada para el control de inventario, cálculo de costos unitarios reales, gestión de márgenes de ganancia y operaciones de Punto de Venta (POS). Desarrollada bajo los principios de **Clean Architecture** (Arquitectura Limpia), la aplicación garantiza un desacoplamiento rígido entre las reglas de negocio, el hardware, la persistencia de datos y la interfaz gráfica.

---

## 🚀 Características Principales

### 🎯 Arquitectura Limpia Estricta (Clean Architecture)
*   **Separación en 4 capas:** Dominio, Casos de Uso, Datos (SQLite) e Infraestructura de Hardware (Impresora Térmica).
*   **Desacoplamiento Total:** La lógica central de cobro e impuestos es completamente agnóstica de la interfaz de usuario CustomTkinter y de la base de datos física.

### 🛡️ Postura de Seguridad (Zero Trust) y Auditoría (Audit Trail)
*   **Prevención de Inyecciones (SQLi):** Cero uso de f-strings, formateo o concatenación manual en sentencias SQL. Todas las operaciones de base de datos emplean consultas parametrizadas rigurosas.
*   **Sanitización Dinámica:** Validación rigurosa de tipo de dato, formato y longitudes máximas (ej. Cajero ID limitado a 15 caracteres alfanuméricos) en la capa de presentación antes de ingresar a capas internas.
*   **Registro de Auditoría:** Todas las operaciones críticas de negocio (anulaciones de tickets, modificaciones manuales de precios, aplicación de descuentos especiales o cierres de caja) se registran de forma obligatoria en la tabla persistente de auditoría `logs_auditoria`, registrando la marca de tiempo exacta, identificador de sesión del cajero y los estados anteriores/nuevos.

### 💼 Robustez de Datos (Transacciones ACID)
*   **Integridad Transaccional:** El registro completo de una venta y la correspondiente deducción física del stock se ejecutan estrictamente dentro de un bloque transaccional atómico (`BEGIN TRANSACTION` y `COMMIT`).
*   **Estrategia de Rollback:** Ante cualquier fallo en el guardado del ticket o stock insuficiente en tiempo real, se ejecuta inmediatamente un `ROLLBACK`, previniendo estados inconsistentes de la base de datos.

### ⚙️ Resiliencia ante Fallos de Hardware
*   **Aislamiento Físico:** Los fallos del canal de impresión térmica (ausencia de papel, atasco físico, USB desconectado o bloqueo de cola de impresión) son capturados de forma específica en la capa de Infraestructura (`PrinterError`).
*   **Operación No Bloqueante:** Estos fallos físicos bajo ninguna circunstancia cuelgan o congelan la aplicación principal. El sistema confirma la venta en la base de datos de manera exitosa y ofrece al cajero un aviso visual no bloqueante en color rojo con la opción de **"Reintentar Impresión"** una vez que el problema del hardware sea solucionado.

### 📊 Interfaz Gráfica Moderna e Interactiva
*   **Estética Catppuccin Mocha:** Tema oscuro optimizado con CustomTkinter para ofrecer una experiencia fluida, rápida y estéticamente moderna.
*   **Pestañas Integradas:**
    1.  **Gestión de Inventario:** Formulario interactivo con cálculos en tiempo real de ganancia neta, costo real y precio sugerido, soportando la edición de stock y unidades disponibles.
    2.  **Terminal POS:** Terminal de cobro ágil. Incluye buscador predictivo del catálogo de productos, carrito interactivo para ajustar cantidades, control de descuentos especiales y efectivo recibido, además de un toggle de simulación de fallos físicos para auditorías de software.
    3.  **Auditoría de Ventas:** Visor de ventas detalladas, herramienta para la **Anulación transaccional de tickets** con restauración automática de existencias, control de cierres de caja financieros y visor del histórico de la bitácora de auditoría (*Audit Trail*).

---

## 📁 Estructura del Proyecto

El proyecto se organiza bajo los estándares profesionales de arquitectura limpia:

```text
/home/andino/Workspace/Python/Kosto/
├── domain/                      # Capa de Dominio (Reglas de Negocio Puras)
│   ├── models.py                # Entidades nucleares (Producto, Venta, DetalleVenta, LogAuditoria) con precisión Decimal
│   └── use_cases.py             # Capa de Casos de Uso (POSUseCase para flujos de cobro, cierres y anulaciones)
├── infrastructure/              # Capa de Infraestructura (Persistencia y Hardware)
│   ├── database.py              # Administrador SQLite3 (DatabaseManager) con transacciones ACID parametrizadas
│   └── printer.py               # Driver y emulador de Impresora Térmica (ThermalPrinter) con control de fallos
├── presentation/                # Capa de Presentación (Interfaz de Usuario)
│   └── gui.py                   # UI basada en pestañas con CustomTkinter usando colores de Catppuccin Mocha
├── test_kosto.py                # Suite de 17 pruebas unitarias y de integración para validar dominio, ACID y resiliencia
├── main.py                      # Punto de entrada principal (Inicialización e Inyección de Dependencias)
├── pyproject.toml               # Configuración de dependencias, Ruff y Mypy
├── uv.lock                      # Bloqueo reproducible de versiones de dependencias para uv
└── LICENSE                      # Licencia Apache 2.0
```

---

## 🛠️ Requisitos del Sistema

*   **Python:** `== 3.12.*` (Estricto)
*   **Gestor de paquetes:** `uv` (Recomendado para una instalación rápida y predecible) o en su defecto `pip` + `venv`.

---

## ⚙️ Instalación y Configuración

### Opción A: Usando `uv` (Recomendado)

Si tienes instalado `uv` en tu sistema:

1.  Clona el repositorio o ubícate en la carpeta del proyecto.
2.  Instala las dependencias y prepara el entorno virtual automáticamente:
    ```bash
    uv sync
    ```

### Opción B: Usando `pip` y entorno virtual tradicional

Si prefieres usar las herramientas estándar de Python:

1.  Crea un entorno virtual de Python 3.12:
    ```bash
    python3.12 -m venv .venv
    ```
2.  Activa el entorno virtual:
    *   **En Linux/macOS:**
        ```bash
        source .venv/bin/activate
        ```
    *   **En Windows (PowerShell):**
        ```powershell
        .venv\Scripts\Activate.ps1
        ```
    *   **En Windows (CMD):**
        ```cmd
        .venv\Scripts\activate.bat
        ```
3.  Instala las dependencias necesarias:
    ```bash
    pip install customtkinter==5.2.2
    ```

---

## 💻 Ejecución

Para iniciar la aplicación:

### Con `uv`:
```bash
uv run main.py
```

### Con `pip` / entorno virtual activo:
```bash
python main.py
```

*Nota: Al iniciar el sistema por primera vez, se creará un archivo de base de datos local llamado `kosto.db` en el mismo directorio de ejecución de forma automática, inicializando las tablas de productos, ventas, detalles y logs de auditoría sin interferir con datos preexistentes.*

---

## 🧪 Pruebas Unitarias e Integración

El proyecto incluye una amplia suite de **17 pruebas automáticas** con `unittest` para validar tanto las fórmulas matemáticas de dominio como el comportamiento de persistencia transaccional (usando SQLite3 `:memory:`) y el manejo de resiliencia física de la impresora.

Para ejecutar los tests:

### Con `uv`:
```bash
uv run python -m unittest test_kosto.py
```

### Con Python tradicional:
```bash
python -m unittest test_kosto.py
```

---

## 🔍 Calidad de Código y Estilo

El proyecto está configurado para mantener altos estándares de calidad utilizando `ruff` y `mypy` bajo una configuración estricta.

### 1. Verificación de Tipos Estáticos (`mypy`)
```bash
uv run mypy .
```

### 2. Formateo y Análisis Estático (`ruff`)
*   **Análisis de linter:**
    ```bash
    uv run ruff check .
    ```
*   **Formatear automáticamente según estándares del proyecto:**
    ```bash
    uv run ruff format .
    ```

---

## 📦 Compilación y Distribución

Para generar un ejecutable autónomo utilizando PyInstaller (incluido en las dependencias de desarrollo) compatible con Windows y Linux de forma automatizada mediante `uv`:

```bash
uv run pyinstaller --noconsole --onefile main.py
```

El ejecutable resultante estará disponible en la carpeta `dist/`.

---

## 📄 Licencia

Este proyecto está bajo la Licencia **Apache 2.0**. Consulta el archivo [LICENSE](LICENSE) para obtener más detalles.

---

*Desarrollado profesionalmente con enfoque en Arquitectura Limpia, Seguridad Zero Trust y Resiliencia de Software.*
