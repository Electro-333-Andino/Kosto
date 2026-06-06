"""
main.py

Punto de entrada principal de la aplicación Kosto.
Orquesta e inicializa las dependencias siguiendo Clean Architecture:
Crea el DatabaseManager (infraestructura) y lo inyecta en KostoApp (presentación).
"""

import customtkinter as ctk

from infrastructure.database import DatabaseManager
from presentation.gui import KostoApp


def main() -> None:
    """
    Función de arranque principal del sistema.
    """
    # Configurar apariencia global de CustomTkinter
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    # Inicializar base de datos (Infraestructura)
    # Se crea el archivo local 'kosto.db' en el directorio de ejecución
    db_manager = DatabaseManager("kosto.db")

    # Inicializar e inyectar dependencia en la GUI (Presentación)
    app = KostoApp(db=db_manager)

    # Iniciar ciclo de eventos principal
    app.mainloop()


if __name__ == "__main__":
    main()
