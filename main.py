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
