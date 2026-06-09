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
infrastructure/database.py

Este módulo maneja la persistencia de datos en SQLite3.
Implementa operaciones CRUD seguras usando consultas parametrizadas para evitar inyecciones SQL.
"""

import sqlite3
from typing import List, Optional

from domain.models import Producto


class DatabaseManager:
    """
    Administrador de la base de datos SQLite3 para el sistema Kosto.
    Garantiza que todas las consultas estén parametrizadas para evitar inyección SQL.
    """

    def __init__(self, db_path: str = "kosto.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Usar sqlite3.Row para acceder a columnas de forma segura por su nombre
        self.conn.row_factory = sqlite3.Row
        self.inicializar_db()

    def inicializar_db(self) -> None:
        """
        Crea la tabla 'productos' si no existe en la base de datos.
        """
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    costo_total REAL NOT NULL,
                    unidades_por_paquete INTEGER NOT NULL,
                    costo_unitario_real REAL NOT NULL,
                    precio_sugerido REAL NOT NULL,
                    precio_manual REAL NOT NULL,
                    ganancia_neta REAL NOT NULL
                )
            """)

    def insertar_producto(self, producto: Producto) -> Producto:
        """
        Inserta un nuevo producto en la base de datos y le asigna el ID autogenerado.
        Garantiza que los campos de tipo Decimal de Python se conviertan a float para SQLite.
        """
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO productos (
                    nombre,
                    costo_total,
                    unidades_por_paquete,
                    costo_unitario_real,
                    precio_sugerido,
                    precio_manual,
                    ganancia_neta
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    producto.nombre,
                    float(producto.costo_total),
                    producto.unidades_por_paquete,
                    float(producto.costo_unitario_real),
                    float(producto.precio_sugerido),
                    float(producto.precio_manual),
                    float(producto.ganancia_neta),
                ),
            )
            producto.id = cursor.lastrowid
        return producto

    def actualizar_producto(self, producto: Producto) -> None:
        """
        Actualiza los datos de un producto existente en la base de datos.
        """
        if producto.id is None:
            raise ValueError("No se puede actualizar un producto sin un ID válido.")

        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE productos
                SET nombre = ?,
                    costo_total = ?,
                    unidades_por_paquete = ?,
                    costo_unitario_real = ?,
                    precio_sugerido = ?,
                    precio_manual = ?,
                    ganancia_neta = ?
                WHERE id = ?
            """,
                (
                    producto.nombre,
                    float(producto.costo_total),
                    producto.unidades_por_paquete,
                    float(producto.costo_unitario_real),
                    float(producto.precio_sugerido),
                    float(producto.precio_manual),
                    float(producto.ganancia_neta),
                    producto.id,
                ),
            )

    def obtener_productos(self, busqueda: Optional[str] = None) -> List[Producto]:
        """
        Obtiene la lista de todos los productos.
        Si se pasa el parámetro 'busqueda', filtra por el nombre del producto de forma segura.
        """
        cursor = self.conn.cursor()
        if busqueda and busqueda.strip():
            # Consulta segura y parametrizada contra inyección SQL
            cursor.execute(
                """
                SELECT id, nombre, costo_total, unidades_por_paquete, precio_manual
                FROM productos
                WHERE nombre LIKE ?
                ORDER BY id DESC
            """,
                (f"%{busqueda.strip()}%",),
            )
        else:
            cursor.execute("""
                SELECT id, nombre, costo_total, unidades_por_paquete, precio_manual
                FROM productos
                ORDER BY id DESC
            """)
        rows = cursor.fetchall()

        productos = []
        for row in rows:
            # Al instanciar, __post_init__ recalcula automáticamente los campos derivados.
            # Pasamos precio_manual de la DB para preservar la sobreescritura del usuario.
            prod = Producto(
                id=row["id"],
                nombre=row["nombre"],
                costo_total=row["costo_total"],
                unidades_por_paquete=row["unidades_por_paquete"],
                precio_manual=row["precio_manual"],
            )
            productos.append(prod)
        return productos

    def eliminar_producto(self, producto_id: int) -> None:
        """
        Elimina de manera segura un producto por su ID.
        """
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))

    def cerrar_conexion(self) -> None:
        """
        Cierra la conexión con la base de datos.
        """
        self.conn.close()
