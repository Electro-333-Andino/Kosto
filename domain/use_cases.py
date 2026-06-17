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
domain/use_cases.py

Este módulo implementa la capa de Casos de Uso (Lógica de Negocio).
Contiene los flujos principales del POS: procesar venta, anular venta,
modificar precio manual, realizar cierre de caja.
Es agnóstico de CustomTkinter y de la tecnología de base de datos directa
(interactúa a través del DatabaseManager de forma abstracta).
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from domain.models import DetalleVenta, LogAuditoria, Venta
from infrastructure.database import DatabaseManager
from infrastructure.printer import PrinterError, ThermalPrinter


class POSUseCase:
    """
    Controlador de Casos de Uso para el módulo POS Kosto.
    """

    def __init__(self, db_manager: DatabaseManager, printer: ThermalPrinter) -> None:
        self.db = db_manager
        self.printer = printer

    def procesar_pago_efectivo(
        self,
        items: list[dict[str, Any]],
        pago_con: Decimal,
        cajero_id: str,
        descuento: Decimal = Decimal("0.00"),
    ) -> tuple[Venta, str | None]:
        """
        Flujo para procesar una venta en efectivo:
        1. Valida el stock físico de cada producto en tiempo real (Capa de Casos
           de Uso).
        2. Calcula los impuestos (16% IVA), el total y el vuelto/cambio usando
           precisión Decimal.
        3. Registra la venta, los detalles y descuenta el inventario bajo una
           transacción ACID estricta.
        4. Si el descuento es especial (>0), registra un evento en la tabla
           de auditoría.
        5. Intenta imprimir el ticket. Si la impresora falla (PrinterError),
           captura el error y retorna un mensaje no bloqueante para que la UI
           pueda ofrecer la opción de reintento, garantizando que la venta se
           guarde con éxito independientemente del estado físico del hardware.
        """
        # Formar los detalles de venta
        detalles_venta: list[DetalleVenta] = []
        for item in items:
            p_id = item["producto_id"]
            cant = item["cantidad"]

            # Obtener el producto de la DB para validar stock y obtener precio
            prod_db = self.db.obtener_producto_por_id(p_id)
            if not prod_db:
                raise ValueError(f"El producto con ID {p_id} no existe.")

            # Validación en tiempo real de stock
            if prod_db.stock < cant:
                raise ValueError(
                    f"Existencias insuficientes para '{prod_db.nombre}'. "
                    f"Solicitado: {cant}, Disponible: {prod_db.stock}."
                )

            precio_unitario = (
                prod_db.precio_manual
                if prod_db.precio_manual is not None
                else prod_db.precio_sugerido
            )

            det_val = DetalleVenta(
                producto_id=p_id,
                nombre_producto=prod_db.nombre,
                cantidad=cant,
                precio_unitario=precio_unitario,
            )
            detalles_venta.append(det_val)

        # Instanciar entidad Venta para validar reglas de negocio
        # y hacer cálculos de impuestos/cambio
        fecha_hora_actual = datetime.now().isoformat()
        venta = Venta(
            detalles=detalles_venta,
            pago_con=pago_con,
            cajero_id=cajero_id,
            descuento=descuento,
            fecha_hora=fecha_hora_actual,
        )

        # Guardar en base de datos dentro de una transacción ACID
        venta_guardada = self.db.registrar_venta_y_deducir_stock(venta)

        # Auditoría: Si hay descuento especial, registrar en logs
        if descuento > Decimal("0.00"):
            log_descuento = LogAuditoria(
                fecha_hora=fecha_hora_actual,
                cajero_id=cajero_id,
                operacion="DESCUENTO_ESPECIAL",
                estado_anterior="Descuento: $0.00",
                estado_nuevo=f"Descuento: ${descuento:.2f}",
                detalles=(
                    f"Se aplicó un descuento especial de ${descuento:.2f} "
                    f"en la Venta ID {venta_guardada.id}"
                ),
            )
            self.db.registrar_log_auditoria(log_descuento)

        # Intentar imprimir ticket
        error_impresora = None

        # Estructurar datos para la impresora
        ticket_data = {
            "venta_id": venta_guardada.id,
            "fecha_hora": venta_guardada.fecha_hora,
            "cajero_id": venta_guardada.cajero_id,
            "subtotal": float(venta_guardada.subtotal),
            "descuento": float(venta_guardada.descuento),
            "impuesto": float(venta_guardada.impuesto),
            "total": float(venta_guardada.total),
            "pago_con": float(venta_guardada.pago_con),
            "cambio": float(venta_guardada.cambio),
            "detalles": [
                {
                    "nombre": d.nombre_producto,
                    "cantidad": d.cantidad,
                    "precio_unitario": float(d.precio_unitario),
                    "subtotal": float(d.subtotal),
                }
                for d in venta_guardada.detalles
            ],
        }

        try:
            self.printer.imprimir_ticket(ticket_data)
        except PrinterError as pe:
            # Capturamos específicamente fallos de hardware
            error_impresora = str(pe)

        return venta_guardada, error_impresora

    def reintentar_impresion(self, venta: Venta) -> tuple[bool, str | None]:
        """
        Permite reintentar la impresión de un ticket si falló anteriormente.
        """
        ticket_data = {
            "venta_id": venta.id,
            "fecha_hora": venta.fecha_hora,
            "cajero_id": venta.cajero_id,
            "subtotal": float(venta.subtotal),
            "descuento": float(venta.descuento),
            "impuesto": float(venta.impuesto),
            "total": float(venta.total),
            "pago_con": float(venta.pago_con),
            "cambio": float(venta.cambio),
            "detalles": [
                {
                    "nombre": d.nombre_producto,
                    "cantidad": d.cantidad,
                    "precio_unitario": float(d.precio_unitario),
                    "subtotal": float(d.subtotal),
                }
                for d in venta.detalles
            ],
        }
        try:
            self.printer.imprimir_ticket(ticket_data)
            return True, None
        except PrinterError as pe:
            return False, str(pe)

    def anular_ticket(self, venta_id: int, cajero_id: str) -> None:
        """
        Anula un ticket de venta:
        1. Devuelve el stock deducido de cada producto.
        2. Marca la venta como 'ANULADA'.
        3. Registra la anulación en la tabla de auditoría.
        Ejecuta todo en una transacción ACID.
        """
        fecha_hora_actual = datetime.now().isoformat()
        self.db.anular_venta_y_restaurar_stock(venta_id, cajero_id, fecha_hora_actual)

    def modificar_precio_manual_con_auditoria(
        self, producto_id: int, nuevo_precio: Decimal, cajero_id: str
    ) -> None:
        """
        Modifica el precio manual de un producto y registra obligatoriamente
        el cambio en la tabla de auditoría.
        """
        prod_db = self.db.obtener_producto_por_id(producto_id)
        if not prod_db:
            raise ValueError(f"El producto con ID {producto_id} no existe.")

        precio_anterior = (
            prod_db.precio_manual
            if prod_db.precio_manual is not None
            else prod_db.precio_sugerido
        )

        # Actualizar precio
        prod_db.update_precio_manual(nuevo_precio)
        self.db.actualizar_producto(prod_db)

        # Registrar auditoría
        fecha_hora_actual = datetime.now().isoformat()
        log_precio = LogAuditoria(
            fecha_hora=fecha_hora_actual,
            cajero_id=cajero_id,
            operacion="MODIFICACION_PRECIO",
            estado_anterior=f"Precio anterior: ${precio_anterior:.2f}",
            estado_nuevo=f"Precio nuevo: ${nuevo_precio:.2f}",
            detalles=(
                f"Se modificó el precio manual de '{prod_db.nombre}' "
                f"(ID: {producto_id})"
            ),
        )
        self.db.registrar_log_auditoria(log_precio)

    def realizar_cierre_de_caja(self, cajero_id: str) -> dict[str, Any]:
        """
        Realiza el cierre de caja de la sesión activa:
        1. Calculates total sales, cobros, etc. of active sessions.
        2. Registra el evento de cierre en Logs_Auditoria.
        """
        # Calcular sumatorias de ventas activas
        resumen = self.db.obtener_resumen_ventas_activas(cajero_id)

        fecha_hora_actual = datetime.now().isoformat()
        detalles_cierre = (
            f"Cierre de caja de {cajero_id}. "
            f"Ventas totales: {resumen['cantidad_ventas']}. "
            f"Monto total: ${resumen['total_ventas']:.2f}. "
            f"Descuentos aplicados: ${resumen['total_descuentos']:.2f}."
        )

        log_cierre = LogAuditoria(
            fecha_hora=fecha_hora_actual,
            cajero_id=cajero_id,
            operacion="CIERRE_CAJA",
            estado_anterior="Caja: ABIERTA",
            estado_nuevo="Caja: CERRADA",
            detalles=detalles_cierre,
        )
        self.db.registrar_log_auditoria(log_cierre)

        # Cambiar estado a cerradas
        self.db.marcar_ventas_como_cerradas(cajero_id)

        return resumen
