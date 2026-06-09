# Kosto — Sistema Profesional de Gestión de Inventario y Márgenes

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-black.svg)](pyproject.toml)
[![Type Checker](https://img.shields.io/badge/type_checker-mypy-blue.svg)](pyproject.toml)

**Kosto** es una aplicación de escritorio diseñada para el control profesional de inventario, cálculo de costos unitarios reales y gestión de márgenes de ganancia. Diseñada bajo los principios de **Clean Architecture** (Arquitectura Limpia), la aplicación garantiza un desacoplamiento total entre sus reglas de negocio, la persistencia de datos y la interfaz gráfica.

---

## 🚀 Características Principales

*   **Arquitectura Limpia:** Separación rígida de capas (Dominio, Infraestructura y Presentación).
*   **Precisión Financiera:** Cálculos matemáticos y comerciales implementados con la librería `Decimal` de Python, eliminando por completo los errores de redondeo inherentes al punto flotante.
*   **Base de Datos Segura:** Almacenamiento local mediante SQLite3 con consultas 100% parametrizadas para prevenir ataques de inyección SQL.
*   **Interfaz Gráfica de Alto Impacto:** Desarrollada con `customtkinter`, adoptando una estética moderna inspirada en la paleta de colores **Catppuccin Mocha** (tema oscuro) y optimizada para la usabilidad.
*   **Búsqueda Interactiva:** Barra de búsqueda integrada con temporización (*debouncing*) para minimizar la carga sobre el motor de persistencia.
*   **Gestor de Paquetes UV:** Configurada con `uv` para una resolución de dependencias ultra rápida y reproducible.

---

## 📁 Estructura del Proyecto

El proyecto se organiza bajo una arquitectura limpia estructurada en las siguientes capas:

```text
/home/andino/Workspace/Python/Kosto/
├── domain/                      # Capa de Dominio (Reglas de Negocio Puras)
│   └── models.py                # Modelo 'Producto' y lógica de cálculos comerciales con Decimal
├── infrastructure/              # Capa de Infraestructura (Persistencia y Datos)
│   └── database.py              # Administrador de SQLite3 (DatabaseManager) y operaciones CRUD
├── presentation/                # Capa de Presentación (Interfaz de Usuario)
│   └── gui.py                   # UI moderna de escritorio basada en CustomTkinter (Catppuccin Mocha)
├── test_kosto.py                # Suite de pruebas unitarias (unittest) para dominio e integración
├── main.py                      # Punto de entrada principal (Inicialización e Inyección de Dependencias)
├── pyproject.toml               # Configuración del proyecto, dependencias, Ruff y Mypy
├── uv.lock                      # Bloqueo de versiones de dependencias para uv
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

*Nota: Al iniciar el sistema por primera vez, se creará un archivo de base de datos local llamado `kosto.db` en el mismo directorio de ejecución de forma automática.*

---

## 🧪 Pruebas Unitarias

El proyecto incluye una suite completa de pruebas unitarias con `unittest` (librería estándar de Python) para validar tanto las fórmulas del modelo de dominio como el comportamiento de persistencia (usando SQLite3 `:memory:`).

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

Para generar un ejecutable autónomo utilizando PyInstaller (incluido en las dependencias de desarrollo):

```bash
uv run pyinstaller --noconsole --onefile main.py
```

El ejecutable resultante estará disponible en la carpeta `dist/`.

---

## 📄 Licencia

Este proyecto está bajo la Licencia **Apache 2.0**. Consulta el archivo [LICENSE](LICENSE) para obtener más detalles.

---

*Desarrollado profesionalmente con enfoque en Arquitectura Limpia y Calidad de Software.*
