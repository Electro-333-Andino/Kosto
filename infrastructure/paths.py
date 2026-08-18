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
infrastructure/paths.py

Gestión de rutas para el despliegue en Windows 10 aislado (sin internet):
- El ejecutable residirá en C:\\Program Files\\Kosto (directorio de solo lectura).
- Los datos de la aplicación (base de datos SQLite y logs) deben ubicarse
  obligatoriamente en %PROGRAMDATA%\\Kosto (típicamente C:\\ProgramData\\Kosto).
- Incluye un resolver de recursos empaquetados (sys._MEIPASS) para que los
  assets (íconos, imágenes, fuentes) funcionen tras la compilación con PyInstaller.
"""

import os
import sys
from pathlib import Path


class KostoPaths:
    """
    Resuelve y garantiza la estructura de carpetas de datos de Kosto
    antes de que cualquier capa intente conectar con la base de datos.
    """

    def __init__(self) -> None:
        # En Windows, %PROGRAMDATA% apunta a C:\\ProgramData.
        program_data = os.environ.get("PROGRAMDATA")
        if program_data:
            self.data_dir: Path = Path(program_data) / "Kosto"
        else:
            # Modo desarrollo sin Windows (Linux/macOS): carpeta local del workspace.
            self.data_dir = Path.cwd() / "kosto_data"

        self.logs_dir = self.data_dir / "logs"
        self.db_path = self.data_dir / "kosto.db"
        self.tickets_log_path = self.logs_dir / "ultimos_tickets.log"

    def ensure_structure(self) -> None:
        """
        Crea la estructura de carpetas de datos si no existe.
        Debe ejecutarse en el arranque, antes de conectar a la base de datos,
        porque Program Files es de solo lectura y la BD debe vivir en ProgramData.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def resolver_recurso(nombre_relativo: str) -> Path:
        """
        Resuelve la ruta absoluta de un recurso empaquetado (íconos, imágenes,
        fuentes). Cuando la aplicación corre dentro del binario de PyInstaller,
        usa sys._MEIPASS; en desarrollo resuelve desde la raíz del proyecto.
        """
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base = Path(str(meipass))
        else:
            base = Path(__file__).resolve().parent.parent
        return base / nombre_relativo
