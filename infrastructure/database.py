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
Implementa operaciones CRUD seguras usando consultas
parametrizadas para evitar inyecciones SQL, y transacciones ACID.
"""

from __future__ import annotations

import functools
import sqlite3
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Any, cast

from domain.models import LogAuditoria, Producto, Venta


class DatabaseOperationError(Exception):
    """
    Excepción de infraestructura con mensaje limpio para la capa de presentación.
    Se eleva cuando SQLite no puede acceder al archivo físico (permisos de
    escritura restringidos por Windows, archivo bloqueado por otro proceso,
    disco lleno, etc.) en lugar de propagar errores técnicos de sqlite3.
    """


def _convertir_errores_sqlite[F: Callable[..., Any]](func: F) -> F:
    """
    Decorador que convierte errores técnicos de sqlite3 en DatabaseOperationError
    con un mensaje accionable, para que la UI muestre un aviso limpio y la
    aplicación jamás crashee por un fallo de permisos o bloqueo del archivo.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except DatabaseOperationError:
            raise
        except sqlite3.Error as err:
            raise DatabaseOperationError(
                "No se pudo acceder a la base de datos. "
                "Verifique que %PROGRAMDATA%\\Kosto tenga permisos de escritura "
                "y que el archivo kosto.db no esté bloqueado por otro proceso."
            ) from err

    return cast(F, wrapper)


class DatabaseManager:
    """
    Administrador de la base de datos SQLite3 para el sistema Kosto.
    Garantiza que todas las consultas estén parametrizadas para evitar
    inyección SQL.
    """

    def __init__(self, db_path: str | Path = "kosto.db"):
        self.db_path = str(db_path)
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        except sqlite3.Error as err:
            raise DatabaseOperationError(
                f"No se pudo conectar a la base de datos en {self.db_path}. "
                "Verifique los permisos de escritura y que la ruta exista."
            ) from err
        # Usar sqlite3.Row para acceder a columnas de forma segura por su nombre
        self.conn.row_factory = sqlite3.Row
        self.inicializar_db()

    def __enter__(self) -> DatabaseManager:
        """Permite usar el administrador como context manager y cerrar la conexión."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Cierra la conexión al salir del bloque with, evitando corrupción de datos."""
        self.cerrar_conexion()

    @_convertir_errores_sqlite
    def inicializar_db(self) -> None:
        """
        Crea la tabla 'productos' si no existe, y añade las tablas necesarias
        para el módulo POS Kosto (ventas, detalles_venta, logs_auditoria)
        de forma compatible con bases de datos preexistentes.
        """
        with self.conn:
            cursor = self.conn.cursor()

            # Crear tabla productos básica si no existe
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

            # Verificar si existe la columna stock, si no, agregarla
            cursor.execute("PRAGMA table_info(productos)")
            columnas = [row["name"] for row in cursor.fetchall()]
            if "stock" not in columnas:
                cursor.execute(
                    "ALTER TABLE productos ADD COLUMN stock INTEGER DEFAULT 0"
                )

            # Crear tabla ventas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_hora TEXT NOT NULL,
                    subtotal REAL NOT NULL,
                    impuesto REAL NOT NULL,
                    descuento REAL NOT NULL,
                    total REAL NOT NULL,
                    pago_con REAL NOT NULL,
                    cambio REAL NOT NULL,
                    cajero_id TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'COMPLETADA'
                )
            """)

            # Crear tabla detalles_venta
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalles_venta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venta_id INTEGER NOT NULL,
                    producto_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY(venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                    FOREIGN KEY(producto_id) REFERENCES productos(id)
                )
            """)

            # Crear tabla logs_auditoria
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs_auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_hora TEXT NOT NULL,
                    cajero_id TEXT NOT NULL,
                    operacion TEXT NOT NULL,
                    estado_anterior TEXT,
                    estado_nuevo TEXT,
                    detalles TEXT
                )
            """)

    @_convertir_errores_sqlite
    def insertar_producto(self, producto: Producto) -> Producto:
        """
        Inserta un nuevo producto en la base de datos y le asigna el ID
        autogenerado.
        Garantiza que los campos de tipo Decimal de Python se conviertan
        a float para SQLite.
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
                    ganancia_neta,
                    stock
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    producto.nombre,
                    float(producto.costo_total),
                    producto.unidades_por_paquete,
                    float(producto.costo_unitario_real),
                    float(producto.precio_sugerido),
                    float(producto.precio_manual)
                    if producto.precio_manual is not None
                    else None,
                    float(producto.ganancia_neta),
                    producto.stock,
                ),
            )
            row_id = cursor.lastrowid

            if row_id is None:
                raise OSError("No se pudo obtener el ID autogenerado.")

            producto.id = row_id

        return producto

    @_convertir_errores_sqlite
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
                    ganancia_neta = ?,
                    stock = ?
                WHERE id = ?
            """,
                (
                    producto.nombre,
                    float(producto.costo_total),
                    producto.unidades_por_paquete,
                    float(producto.costo_unitario_real),
                    float(producto.precio_sugerido),
                    float(
                        producto.precio_manual
                        if producto.precio_manual is not None
                        else producto.precio_sugerido
                    ),
                    float(producto.ganancia_neta),
                    producto.stock,
                    producto.id,
                ),
            )

    @_convertir_errores_sqlite
    def obtener_productos(self, busqueda: str | None = None) -> list[Producto]:
        """
        Obtiene la lista de todos los productos.
        Si se pasa el parámetro 'busqueda',
        filtra por el nombre del producto de forma segura.
        """
        cursor = self.conn.cursor()
        if busqueda and busqueda.strip():
            # Consulta segura y parametrizada contra inyección SQL
            cursor.execute(
                """
                SELECT id, nombre, costo_total, unidades_por_paquete,
                       precio_manual, stock
                FROM productos
                WHERE nombre LIKE ?
                ORDER BY id DESC
            """,
                (f"%{busqueda.strip()}%",),
            )
        else:
            cursor.execute("""
                SELECT id, nombre, costo_total, unidades_por_paquete,
                       precio_manual, stock
                FROM productos
                ORDER BY id DESC
            """)
        rows = cursor.fetchall()

        productos = []
        for row in rows:
            # Al instanciar, __post_init__ recalcula automáticamente
            # los campos derivados.
            # Pasamos precio_manual de la DB para preservar
            # la sobreescritura del usuario.
            prod = Producto(
                id=row["id"],
                nombre=row["nombre"],
                costo_total=row["costo_total"],
                unidades_por_paquete=row["unidades_por_paquete"],
                precio_manual=row["precio_manual"],
                stock=row["stock"] if "stock" in row.keys() else 0,
            )
            productos.append(prod)
        return productos

    @_convertir_errores_sqlite
    def obtener_producto_por_id(self, producto_id: int) -> Producto | None:
        """
        Obtiene un producto específico por su ID de forma parametrizada.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, nombre, costo_total, unidades_por_paquete, precio_manual, stock
            FROM productos
            WHERE id = ?
        """,
            (producto_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Producto(
            id=row["id"],
            nombre=row["nombre"],
            costo_total=row["costo_total"],
            unidades_por_paquete=row["unidades_por_paquete"],
            precio_manual=row["precio_manual"],
            stock=row["stock"],
        )

    @_convertir_errores_sqlite
    def eliminar_producto(self, producto_id: int) -> None:
        """
        Elimina de manera segura un producto por su ID.
        """
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))

    @_convertir_errores_sqlite
    def registrar_venta_y_deducir_stock(self, venta: Venta) -> Venta:
        """
        Registra una venta con sus detalles y deduce la cantidad del stock
        de cada producto.
        Ejecuta todas las operaciones de forma atómica bajo una transacción única.
        Si alguna operación falla o hay stock insuficiente, realiza un ROLLBACK.
        """
        try:
            with self.conn:
                cursor = self.conn.cursor()

                # 1. Registrar la cabecera de la venta
                cursor.execute(
                    """
                    INSERT INTO ventas (
                        fecha_hora, subtotal, impuesto, descuento,
                        total, pago_con, cambio, cajero_id, estado
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        venta.fecha_hora,
                        float(venta.subtotal),
                        float(venta.impuesto),
                        float(venta.descuento),
                        float(venta.total),
                        float(venta.pago_con),
                        float(venta.cambio),
                        venta.cajero_id,
                        venta.estado,
                    ),
                )
                venta_id = cursor.lastrowid
                if venta_id is None:
                    raise OSError("No se pudo registrar la cabecera de la venta.")
                venta.id = venta_id

                # 2. Registrar los detalles de la venta y deducir stock
                for det in venta.detalles:
                    # Recuperar el stock actual
                    cursor.execute(
                        "SELECT stock, nombre FROM productos WHERE id = ?",
                        (det.producto_id,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise ValueError(
                            f"El producto con ID {det.producto_id} no existe."
                        )

                    stock_actual = row["stock"]
                    nombre_prod = row["nombre"]

                    if stock_actual < det.cantidad:
                        raise ValueError(
                            f"Existencias insuficientes para '{nombre_prod}'. "
                            f"Solicitado: {det.cantidad}, Disponible: {stock_actual}."
                        )

                    # Insertar detalle de venta
                    cursor.execute(
                        """
                        INSERT INTO detalles_venta (
                            venta_id, producto_id, cantidad,
                            precio_unitario, subtotal
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            venta_id,
                            det.producto_id,
                            det.cantidad,
                            float(det.precio_unitario),
                            float(det.subtotal),
                        ),
                    )

                    # Deducir stock
                    nuevo_stock = stock_actual - det.cantidad
                    cursor.execute(
                        "UPDATE productos SET stock = ? WHERE id = ?",
                        (nuevo_stock, det.producto_id),
                    )

            return venta
        except Exception as e:
            # Con el bloque with self.conn, sqlite3 ya efectúa ROLLBACK
            # automáticamente en caso de excepción.
            raise e

    @_convertir_errores_sqlite
    def anular_venta_y_restaurar_stock(
        self, venta_id: int, cajero_id: str, fecha_hora: str
    ) -> None:
        """
        Anula un ticket de venta bajo una única transacción:
        1. Devuelve el stock deducido de cada detalle de la venta.
        2. Marca la venta como 'ANULADA'.
        3. Registra la auditoría correspondiente.
        """
        try:
            with self.conn:
                cursor = self.conn.cursor()

                # 1. Obtener detalles de la venta
                cursor.execute(
                    """
                    SELECT producto_id, cantidad
                    FROM detalles_venta
                    WHERE venta_id = ?
                """,
                    (venta_id,),
                )
                detalles = cursor.fetchall()
                if not detalles:
                    raise ValueError(
                        f"No se encontraron detalles para la Venta ID {venta_id}."
                    )

                # Obtener cabecera para verificar estado y monto
                cursor.execute(
                    "SELECT total, estado FROM ventas WHERE id = ?", (venta_id,)
                )
                venta_row = cursor.fetchone()
                if venta_row is None:
                    raise ValueError(f"La venta con ID {venta_id} no existe.")
                if venta_row["estado"] == "ANULADA":
                    raise ValueError(
                        f"La venta con ID {venta_id} ya se encuentra ANULADA."
                    )

                total_venta = venta_row["total"]

                # 2. Restaurar stock de cada producto
                for det in detalles:
                    p_id = det["producto_id"]
                    cant = det["cantidad"]

                    cursor.execute("SELECT stock FROM productos WHERE id = ?", (p_id,))
                    prod_row = cursor.fetchone()
                    if prod_row is not None:
                        nuevo_stock = prod_row["stock"] + cant
                        cursor.execute(
                            "UPDATE productos SET stock = ? WHERE id = ?",
                            (nuevo_stock, p_id),
                        )

                # 3. Marcar la venta como anulada
                cursor.execute(
                    "UPDATE ventas SET estado = 'ANULADA' WHERE id = ?",
                    (venta_id,),
                )

                # 4. Registrar auditoría de anulación
                cursor.execute(
                    """
                    INSERT INTO logs_auditoria (
                        fecha_hora, cajero_id, operacion,
                        estado_anterior, estado_nuevo, detalles
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fecha_hora,
                        cajero_id,
                        "ANULACION",
                        "Venta: COMPLETADA",
                        "Venta: ANULADA",
                        f"Se anuló la venta ID {venta_id}. "
                        f"Monto devuelto: ${total_venta:.2f}.",
                    ),
                )
        except Exception as e:
            raise e

    @_convertir_errores_sqlite
    def registrar_log_auditoria(self, log: LogAuditoria) -> LogAuditoria:
        """
        Inserta un registro de auditoría en la tabla Logs_Auditoria.
        Usa consultas parametrizadas para prevenir inyecciones SQL.
        """
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO logs_auditoria (
                    fecha_hora, cajero_id, operacion,
                    estado_anterior, estado_nuevo, detalles
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    log.fecha_hora,
                    log.cajero_id,
                    log.operacion,
                    log.estado_anterior,
                    log.estado_nuevo,
                    log.detalles,
                ),
            )
            row_id = cursor.lastrowid
            if row_id is not None:
                log.id = row_id
        return log

    @_convertir_errores_sqlite
    def obtener_logs_auditoria(self) -> list[dict[str, Any]]:
        """
        Retorna todos los registros de auditoría almacenados.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, fecha_hora, cajero_id, operacion,
                   estado_anterior, estado_nuevo, detalles
            FROM logs_auditoria
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @_convertir_errores_sqlite
    def obtener_ventas(self) -> list[dict[str, Any]]:
        """
        Retorna todas las ventas registradas con su estado.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, fecha_hora, subtotal, impuesto, descuento,
                   total, pago_con, cambio, cajero_id, estado
            FROM ventas
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @_convertir_errores_sqlite
    def obtener_detalles_venta(self, venta_id: int) -> list[dict[str, Any]]:
        """
        Retorna los detalles (productos vendidos) de una venta específica,
        para que la capa de presentación jamás acceda directamente a la conexión.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT v.id, v.fecha_hora, v.total, v.estado,
                   d.producto_id, d.cantidad, d.precio_unitario,
                   d.subtotal, p.nombre
            FROM ventas v
            JOIN detalles_venta d ON v.id = d.venta_id
            JOIN productos p ON d.producto_id = p.id
            WHERE v.id = ?
        """,
            (venta_id,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @_convertir_errores_sqlite
    def obtener_resumen_ventas_activas(self, cajero_id: str) -> dict[str, Any]:
        """
        Calcula las métricas de las ventas con estado 'COMPLETADA'
        (no anuladas ni cerradas) para el cajero especificado.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as cant, SUM(total) as tot, SUM(descuento) as desc
            FROM ventas
            WHERE cajero_id = ? AND estado = 'COMPLETADA'
        """,
            (cajero_id,),
        )
        row = cursor.fetchone()
        return {
            "amount": row["cant"] if row["cant"] is not None else 0,
            "cantidad_ventas": row["cant"] if row["cant"] is not None else 0,
            "total_ventas": row["tot"] if row["tot"] is not None else 0.0,
            "total_descuentos": row["desc"] if row["desc"] is not None else 0.0,
        }

    @_convertir_errores_sqlite
    def marcar_ventas_como_cerradas(self, cajero_id: str) -> None:
        """
        Cambia el estado de las ventas de 'COMPLETADA' a 'CERRADA_SESION'
        después del cierre de caja del cajero.
        """
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE ventas
                SET estado = 'CERRADA_SESION'
                WHERE cajero_id = ? AND estado = 'COMPLETADA'
            """,
                (cajero_id,),
            )

    def cerrar_conexion(self) -> None:
        """
        Cierra la conexión con la base de datos.
        """
        self.conn.close()
