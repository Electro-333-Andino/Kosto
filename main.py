# Copyright 2026 Kosto Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
main.py

Punto de entrada principal de la aplicación Kosto.
Orquesta e inicializa las dependencias siguiendo Clean Architecture:
1. Garantiza la estructura de datos en %PROGRAMDATA%\\Kosto (Windows).
2. Crea el DatabaseManager (infraestructura) y lo inyecta en KostoApp (presentación).
3. Cierra la conexión de forma controlada al terminar.
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from infrastructure.database import DatabaseManager, DatabaseOperationError
from infrastructure.paths import KostoPaths
from presentation.gui import KostoApp


def _mostrar_error_fatal(mensaje: str) -> None:
    """
    Muestra un mensaje de error limpio antes de que la ventana principal exista.
    Evita que la aplicación falle silenciosamente o con traceback en consola.
    """
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Kosto - Error de Inicialización", mensaje)
    root.destroy()


def main() -> None:
    """
    Función de arranque principal del sistema.
    """
    # Configurar apariencia global de CustomTkinter
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    # 1. Rutas Windows: el .exe vive en Program Files (solo lectura);
    # la BD y los logs deben crearse en %PROGRAMDATA%\\Kosto ANTES de conectar.
    try:
        paths = KostoPaths()
        paths.ensure_structure()
    except OSError as err:
        _mostrar_error_fatal(
            "No se pudo crear la estructura de datos en %PROGRAMDATA%\\Kosto.\n\n"
            f"Detalle: {err}\n\n"
            "Verifique que el usuario tenga permisos de escritura "
            "sobre la carpeta ProgramData."
        )
        return

    # 2. Conexión a la base de datos con manejo limpio de errores de permisos
    try:
        db_manager = DatabaseManager(paths.db_path)
    except DatabaseOperationError as err:
        _mostrar_error_fatal(str(err))
        return

    try:
        # 3. Inicializar e inyectar dependencias en la GUI (Presentación)
        app = KostoApp(db=db_manager, tickets_log_path=str(paths.tickets_log_path))
        app.mainloop()
    finally:
        # 4. Cierre controlado de la conexión para evitar corrupción de datos
        db_manager.cerrar_conexion()


if __name__ == "__main__":
    main()
