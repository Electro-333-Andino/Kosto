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
test_kosto.py

Suite de pruebas unitarias y de integración para Kosto.
Verifica la lógica de negocio (dominio), persistencia (infraestructura SQLite3),
mecanismo de transacciones ACID, registro de auditoría y resiliencia de hardware.
"""

import unittest
from decimal import Decimal

from domain.models import DetalleVenta, Producto, Venta
from domain.use_cases import POSUseCase
from infrastructure.database import DatabaseManager
from infrastructure.printer import ThermalPrinter


class TestProductoDomain(unittest.TestCase):
    """
    Pruebas unitarias para la lógica del modelo de dominio de Producto.
    """

    def test_calculos_iniciales_exito(self) -> None:
        """
        Verifica que un lote de producto calcule correctamente el costo unitario real,
        el precio sugerido y la ganancia neta.
        Ejemplo: Costo $3.67, Unidades 12, Precio Manual $0.35.
        """
        p = Producto(
            nombre="Aceite de Oliva",
            costo_total=Decimal("3.67"),
            unidades_por_paquete=12,
            precio_manual=Decimal("0.35"),
            stock=10,
        )
        # 3.67 / 12 = 0.305833... -> redondeado a 4 decimales: 0.3058
        self.assertEqual(p.costo_unitario_real, Decimal("0.3058"))
        # Costo unitario real (0.3058) redondeado a 2 decimales: 0.31
        self.assertEqual(p.precio_sugerido, Decimal("0.31"))
        # Ganancia: 0.35 - 0.3058 = 0.0442
        self.assertEqual(p.ganancia_neta, Decimal("0.0442"))
        self.assertEqual(p.stock, 10)

    def test_precio_manual_por_defecto_sugerido(self) -> None:
        """
        Verifica que si no se proporciona un precio manual,
        este tome el valor del precio sugerido,
        y calcule la ganancia correspondiente.
        """
        p = Producto(
            nombre="Harina de Trigo",
            costo_total=Decimal("10.00"),
            unidades_por_paquete=10,
        )
        self.assertEqual(p.costo_unitario_real, Decimal("1.0000"))
        self.assertEqual(p.precio_sugerido, Decimal("1.00"))
        self.assertEqual(p.precio_manual, Decimal("1.00"))
        self.assertEqual(p.ganancia_neta, Decimal("0.00"))

    def test_actualizar_precio_manual_exito(self) -> None:
        """
        Verifica que al actualizar el precio manual,
        la ganancia neta se recalcule de forma correcta.
        """
        p = Producto(
            nombre="Salsa de Tomate",
            costo_total=Decimal("5.00"),
            unidades_por_paquete=10,
        )
        p.update_precio_manual(Decimal("0.75"))

        self.assertEqual(p.precio_manual, Decimal("0.75"))
        self.assertEqual(p.ganancia_neta, Decimal("0.25"))

    def test_validaciones_valores_invalidos(self) -> None:
        """
        Verifica que el modelo de dominio rechace valores inválidos en la creación.
        """
        # Nombre vacío
        with self.assertRaises(ValueError):
            Producto(nombre="", costo_total=Decimal("10.00"), unidades_por_paquete=10)

        # Costo total <= 0
        with self.assertRaises(ValueError):
            Producto(
                nombre="Arroz", costo_total=Decimal("0.0"), unidades_por_paquete=10
            )
        with self.assertRaises(ValueError):
            Producto(
                nombre="Arroz", costo_total=Decimal("-1.5"), unidades_por_paquete=10
            )

        # Unidades por paquete <= 0
        with self.assertRaises(ValueError):
            Producto(
                nombre="Fideos", costo_total=Decimal("5.0"), unidades_por_paquete=0
            )
        with self.assertRaises(ValueError):
            Producto(
                nombre="Fideos", costo_total=Decimal("5.0"), unidades_por_paquete=-5
            )

        # Precio manual negativo
        with self.assertRaises(ValueError):
            Producto(
                nombre="Fideos",
                costo_total=Decimal("5.0"),
                unidades_por_paquete=5,
                precio_manual=Decimal("-0.5"),
            )

        # Stock negativo
        with self.assertRaises(ValueError):
            Producto(
                nombre="Fideos",
                costo_total=Decimal("5.0"),
                unidades_por_paquete=5,
                stock=-1,
            )

    def test_actualizar_precio_manual_invalido(self) -> None:
        """
        Verifica que no se permita establecer un precio manual negativo.
        """
        p = Producto(
            nombre="Leche", costo_total=Decimal("4.50"), unidades_por_paquete=5
        )
        with self.assertRaises(ValueError):
            p.update_precio_manual(Decimal("-0.1"))


class TestDetalleYVentaDomain(unittest.TestCase):
    """
    Pruebas unitarias para las entidades de dominio DetalleVenta y Venta.
    """

    def test_detalle_venta_calculos(self) -> None:
        det = DetalleVenta(
            producto_id=1,
            nombre_producto="Aceite",
            cantidad=3,
            precio_unitario=Decimal("1.50"),
        )
        self.assertEqual(det.subtotal, Decimal("4.50"))

        with self.assertRaises(ValueError):
            DetalleVenta(
                producto_id=1,
                nombre_producto="Aceite",
                cantidad=0,
                precio_unitario=Decimal("1.50"),
            )

    def test_venta_calculos_sin_descuento(self) -> None:
        det1 = DetalleVenta(
            producto_id=1,
            nombre_producto="Aceite",
            cantidad=2,
            precio_unitario=Decimal("1.50"),
        )
        det2 = DetalleVenta(
            producto_id=2,
            nombre_producto="Arroz",
            cantidad=1,
            precio_unitario=Decimal("2.00"),
        )

        v = Venta(
            detalles=[det1, det2],
            pago_con=Decimal("10.00"),
            cajero_id="CAJERO-01",
        )

        # Subtotal: 2*1.50 + 1*2.00 = 5.00
        self.assertEqual(v.subtotal, Decimal("5.00"))
        # Impuesto: 5.00 * 0.16 = 0.80
        self.assertEqual(v.impuesto, Decimal("0.80"))
        # Total: 5.00 + 0.80 = 5.80
        self.assertEqual(v.total, Decimal("5.80"))
        # Cambio: 10.00 - 5.80 = 4.20
        self.assertEqual(v.cambio, Decimal("4.20"))

    def test_venta_calculos_con_descuento(self) -> None:
        det = DetalleVenta(
            producto_id=1,
            nombre_producto="Aceite",
            cantidad=10,
            precio_unitario=Decimal("2.00"),
        )

        v = Venta(
            detalles=[det],
            pago_con=Decimal("20.00"),
            cajero_id="CAJERO-01",
            descuento=Decimal("5.00"),
        )

        # Subtotal: 20.00 - 5.00 = 15.00
        self.assertEqual(v.subtotal, Decimal("15.00"))
        # Impuesto: 15.00 * 0.16 = 2.40
        self.assertEqual(v.impuesto, Decimal("2.40"))
        # Total: 15.00 + 2.40 = 17.40
        self.assertEqual(v.total, Decimal("17.40"))
        # Cambio: 20.00 - 17.40 = 2.60
        self.assertEqual(v.cambio, Decimal("2.60"))

    def test_venta_validaciones_pago_insuficiente(self) -> None:
        det = DetalleVenta(
            producto_id=1,
            nombre_producto="Aceite",
            cantidad=1,
            precio_unitario=Decimal("2.00"),
        )
        with self.assertRaises(ValueError):
            Venta(
                detalles=[det],
                pago_con=Decimal("1.00"),
                cajero_id="CAJERO-01",
            )


class TestDatabaseManager(unittest.TestCase):
    """
    Pruebas de integración para el Administrador de Base de Datos.
    Utiliza una base de datos SQLite3 en memoria
    para garantizar aislamiento e idoneidad.
    """

    def setUp(self) -> None:
        self.db = DatabaseManager(":memory:")

    def tearDown(self) -> None:
        self.db.cerrar_conexion()

    def test_db_inicializacion(self) -> None:
        """
        Verifica que las tablas de productos, ventas y auditoría se creen
        correctamente.
        """
        cursor = self.db.conn.cursor()
        tablas = ["productos", "ventas", "detalles_venta", "logs_auditoria"]
        for t in tablas:
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'"
            )
            self.assertIsNotNone(cursor.fetchone(), f"La tabla {t} debería existir.")

    def test_insertar_y_obtener_producto_exito(self) -> None:
        """
        Verifica que un producto se inserte correctamente con su stock.
        """
        p = Producto(
            nombre="Azúcar 1kg",
            costo_total=Decimal("12.50"),
            unidades_por_paquete=10,
            precio_manual=Decimal("1.50"),
            stock=15,
        )
        p_guardado = self.db.insertar_producto(p)
        self.assertEqual(p_guardado.stock, 15)

        productos = self.db.obtener_productos()
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0].stock, 15)

    def test_transaccion_venta_y_deduccion_stock_exito(self) -> None:
        """
        Verifica que registrar una venta descuente de forma correcta
        el stock físico de los productos bajo una transacción.
        """
        p1 = self.db.insertar_producto(
            Producto(
                nombre="Manzana",
                costo_total=Decimal("5.00"),
                unidades_por_paquete=5,
                stock=10,
            )
        )
        p2 = self.db.insertar_producto(
            Producto(
                nombre="Naranja",
                costo_total=Decimal("4.00"),
                unidades_por_paquete=4,
                stock=5,
            )
        )

        det1 = DetalleVenta(
            producto_id=p1.id,
            nombre_producto=p1.nombre,
            cantidad=3,
            precio_unitario=Decimal("1.00"),
        )
        det2 = DetalleVenta(
            producto_id=p2.id,
            nombre_producto=p2.nombre,
            cantidad=2,
            precio_unitario=Decimal("1.20"),
        )

        v = Venta(
            detalles=[det1, det2],
            pago_con=Decimal("10.00"),
            cajero_id="CAJERO-01",
            fecha_hora="2026-06-16T12:00:00",
        )

        venta_guardada = self.db.registrar_venta_y_deducir_stock(v)
        self.assertIsNotNone(venta_guardada.id)

        # Verificar stock actualizado
        prod1_act = self.db.obtener_producto_por_id(p1.id)
        prod2_act = self.db.obtener_producto_por_id(p2.id)
        self.assertEqual(prod1_act.stock, 7)  # 10 - 3
        self.assertEqual(prod2_act.stock, 3)  # 5 - 2

    def test_transaccion_rollback_stock_insuficiente(self) -> None:
        """
        Prueba crítica de ACID: si un producto no tiene suficiente stock,
        toda la transacción se debe revertir (ROLLBACK) y ningún stock debe cambiar.
        """
        p1 = self.db.insertar_producto(
            Producto(
                nombre="Leche",
                costo_total=Decimal("2.00"),
                unidades_por_paquete=2,
                stock=10,
            )
        )
        p2 = self.db.insertar_producto(
            Producto(
                nombre="Queso",
                costo_total=Decimal("3.00"),
                unidades_por_paquete=1,
                stock=1,  # Stock bajo!
            )
        )

        det1 = DetalleVenta(
            producto_id=p1.id,
            nombre_producto=p1.nombre,
            cantidad=5,
            precio_unitario=Decimal("1.00"),
        )
        det2 = DetalleVenta(
            producto_id=p2.id,
            nombre_producto=p2.nombre,
            cantidad=3,  # Reclama 3, disponible 1!
            precio_unitario=Decimal("3.00"),
        )

        v = Venta(
            detalles=[det1, det2],
            pago_con=Decimal("20.00"),
            cajero_id="CAJERO-01",
            fecha_hora="2026-06-16T12:00:00",
        )

        # Debería lanzar error por existencias insuficientes
        with self.assertRaises(ValueError):
            self.db.registrar_venta_y_deducir_stock(v)

        # ACID: El stock de p1 NO debe haber cambiado (se revirtió la deducción)
        prod1_act = self.db.obtener_producto_por_id(p1.id)
        prod2_act = self.db.obtener_producto_por_id(p2.id)
        self.assertEqual(prod1_act.stock, 10)
        self.assertEqual(prod2_act.stock, 1)

        # ACID: La venta no debe haberse guardado
        ventas = self.db.obtener_ventas()
        self.assertEqual(len(ventas), 0)

    def test_anular_venta_y_restaurar_stock_exito(self) -> None:
        """
        Verifica que anular un ticket devuelva el stock y cambie el estado de la venta.
        """
        p = self.db.insertar_producto(
            Producto(
                nombre="Harina",
                costo_total=Decimal("5.00"),
                unidades_por_paquete=5,
                stock=5,
            )
        )
        det = DetalleVenta(
            producto_id=p.id,
            nombre_producto=p.nombre,
            cantidad=3,
            precio_unitario=Decimal("1.00"),
        )
        v = Venta(
            detalles=[det],
            pago_con=Decimal("5.00"),
            cajero_id="CAJERO-01",
            fecha_hora="2026-06-16T12:00:00",
        )

        v_guardada = self.db.registrar_venta_y_deducir_stock(v)
        self.assertEqual(self.db.obtener_producto_por_id(p.id).stock, 2)

        # Anular venta
        self.db.anular_venta_y_restaurar_stock(
            v_guardada.id, "SUPERVISOR", "2026-06-16T13:00:00"
        )

        # Verificar stock restaurado
        self.assertEqual(self.db.obtener_producto_por_id(p.id).stock, 5)

        # Verificar estado venta
        ventas = self.db.obtener_ventas()
        self.assertEqual(ventas[0]["estado"], "ANULADA")


class TestPOSUseCase(unittest.TestCase):
    """
    Pruebas unitarias y de resiliencia física para el caso de uso POSUseCase.
    """

    def setUp(self) -> None:
        self.db = DatabaseManager(":memory:")
        self.printer = ThermalPrinter()
        self.use_case = POSUseCase(self.db, self.printer)

    def tearDown(self) -> None:
        self.db.cerrar_conexion()

    def test_procesar_pago_efectivo_exito(self) -> None:
        """
        Verifica el flujo normal de cobro con impresión exitosa.
        """
        p = self.db.insertar_producto(
            Producto(
                nombre="Chocolate",
                costo_total=Decimal("10.00"),
                unidades_por_paquete=10,
                stock=5,
            )
        )

        items = [{"producto_id": p.id, "cantidad": 2}]

        venta, err_p = self.use_case.procesar_pago_efectivo(
            items=items,
            pago_con=Decimal("5.00"),
            cajero_id="CAJERO-01",
        )

        self.assertIsNone(err_p)
        self.assertEqual(venta.subtotal, Decimal("2.00"))
        # El stock se debió deducir
        self.assertEqual(self.db.obtener_producto_por_id(p.id).stock, 3)

    def test_procesar_pago_efectivo_resiliencia_hardware(self) -> None:
        """
        Caso Crítico de Resiliencia: la impresora falla físicamente,
        pero la venta se confirma correctamente en la base de datos de todos modos.
        """
        p = self.db.insertar_producto(
            Producto(
                nombre="Chocolate",
                costo_total=Decimal("10.00"),
                unidades_por_paquete=10,
                stock=5,
            )
        )

        # Simular fallo físico de la impresora
        self.printer.simular_fallo = True
        self.printer.tipo_fallo = "Atasco de papel"

        items = [{"producto_id": p.id, "cantidad": 2}]

        venta, err_p = self.use_case.procesar_pago_efectivo(
            items=items,
            pago_con=Decimal("5.00"),
            cajero_id="CAJERO-01",
        )

        # Resiliencia: la base de datos se confirmó (venta guardada y stock deducido)
        self.assertIsNotNone(venta.id)
        self.assertEqual(self.db.obtener_producto_por_id(p.id).stock, 3)

        # Pero el sistema retorna un aviso no bloqueante detallando el error físico
        self.assertIsNotNone(err_p)
        self.assertIn("Atasco de papel", err_p)

        # El cajero soluciona el problema físico de la impresora y reintenta
        self.printer.simular_fallo = False
        exito, err_reintento = self.use_case.reintentar_impresion(venta)
        self.assertTrue(exito)
        self.assertIsNone(err_reintento)

    def test_modificar_precio_manual_con_auditoria(self) -> None:
        """
        Verifica que modificar precios guarde un log de auditoría detallado.
        """
        p = self.db.insertar_producto(
            Producto(
                nombre="Aceite",
                costo_total=Decimal("5.00"),
                unidades_por_paquete=5,
                stock=5,
            )
        )

        self.use_case.modificar_precio_manual_con_auditoria(
            p.id, Decimal("1.50"), "SUPERVISOR"
        )

        # Verificar precio actualizado
        prod_act = self.db.obtener_producto_por_id(p.id)
        self.assertEqual(prod_act.precio_manual, Decimal("1.50"))

        # Verificar log en la auditoría
        logs = self.db.obtener_logs_auditoria()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["operacion"], "MODIFICACION_PRECIO")
        self.assertEqual(logs[0]["cajero_id"], "SUPERVISOR")
        self.assertIn("Aceite", logs[0]["detalles"])


if __name__ == "__main__":
    unittest.main()
