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
domain/models.py

Este módulo contiene el modelo de dominio de Kosto.
Define la entidad core de Producto, DetalleVenta, Venta y LogAuditoria,
y maneja todos los cálculos matemáticos y comerciales.
Está completamente desacoplado de bases de datos y de la interfaz de usuario.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


@dataclass
class Producto:
    nombre: str
    costo_total: Decimal
    unidades_por_paquete: int
    precio_manual: Decimal | None = None
    id: int | None = None
    stock: int = 0

    # Campos calculados automáticamente usando precisión de Decimal
    costo_unitario_real: Decimal = field(init=False)
    precio_sugerido: Decimal = field(init=False)
    ganancia_neta: Decimal = field(init=False)

    def __post_init__(self) -> None:
        """
        Valida las propiedades de entrada y calcula automáticamente el costo unitario,
        el precio de venta sugerido y la ganancia neta usando precisión de Decimal.
        """
        # Validación de nombre
        if not self.nombre or not self.nombre.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
        self.nombre = self.nombre.strip()

        # Conversión y validación de costo total
        try:
            if isinstance(self.costo_total, str):
                self.costo_total = Decimal(str(self.costo_total.replace(",", ".")))
            self.costo_total = Decimal(str(self.costo_total))
        except (ValueError, TypeError, InvalidOperation) as err:
            raise ValueError("El costo total debe ser un número válido.") from err

        # Conversión y validación de unidades por paquete
        try:
            self.unidades_por_paquete = int(self.unidades_por_paquete)
        except (ValueError, TypeError) as err:
            raise ValueError(
                "Las unidades por paquete deben ser un número entero válido."
            ) from err

        if self.costo_total <= Decimal("0"):
            raise ValueError("El costo total debe ser mayor que cero.")

        if self.unidades_por_paquete <= 0:
            raise ValueError("Las unidades por paquete deben ser mayores que cero.")

        # Conversión y validación de stock
        try:
            self.stock = int(self.stock)
        except (ValueError, TypeError) as err:
            raise ValueError("El stock debe ser un número entero válido.") from err

        if self.stock < 0:
            raise ValueError("El stock no puede ser negativo.")

        # Costo unitario real (ej. 3.67 / 12 = 0.3058)
        costo_crudo = self.costo_total / Decimal(self.unidades_por_paquete)
        self.costo_unitario_real = costo_crudo.quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        # Precio de venta sugerido (redondeado, ej. 0.31)
        self.precio_sugerido = self.costo_unitario_real.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Si el precio manual no está definido, se inicializa con el precio sugerido
        if self.precio_manual is None:
            self.precio_manual = self.precio_sugerido
        else:
            try:
                if isinstance(self.precio_manual, str):
                    self.precio_manual = Decimal(
                        str(self.precio_manual.replace(",", "."))
                    )
                self.precio_manual = Decimal(str(self.precio_manual))
            except (ValueError, TypeError, InvalidOperation) as err:
                raise ValueError("El precio manual debe ser un número válido.") from err
            if self.precio_manual < Decimal("0"):
                raise ValueError("El precio manual no puede ser negativo.")

        # Cálculo final: Ganancia neta (Precio manual - Costo unitario real)
        self.recalculate_ganancia()

    def update_precio_manual(self, nuevo_precio: Decimal | float | str) -> None:
        """
        Permite actualizar el precio manual de venta y recalcula la ganancia neta.
        """
        try:
            if isinstance(nuevo_precio, str):
                nuevo_precio = nuevo_precio.replace(",", ".")
            nuevo_precio = Decimal(str(nuevo_precio))
        except (ValueError, TypeError, InvalidOperation) as err:
            raise ValueError("El precio manual debe ser un número válido.") from err

        if nuevo_precio < Decimal("0"):
            raise ValueError("El precio manual no puede ser negativo.")

        self.precio_manual = nuevo_precio
        self.recalculate_ganancia()

    def recalculate_ganancia(self) -> None:
        """
        Recalcula la ganancia neta por unidad.
        """
        if self.precio_manual is None:
            self.precio_manual = self.precio_sugerido
        self.ganancia_neta = (self.precio_manual - self.costo_unitario_real).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )


@dataclass
class DetalleVenta:
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal = field(init=False)

    def __post_init__(self) -> None:
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")
        if self.precio_unitario < Decimal("0"):
            raise ValueError("El precio unitario no puede ser negativo.")
        self.subtotal = (Decimal(str(self.cantidad)) * self.precio_unitario).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


@dataclass
class Venta:
    detalles: list[DetalleVenta]
    pago_con: Decimal
    cajero_id: str
    descuento: Decimal = Decimal("0.00")
    id: int | None = None
    fecha_hora: str | None = None
    estado: str = "COMPLETADA"

    # Campos calculados
    subtotal: Decimal = field(init=False)
    impuesto: Decimal = field(init=False)
    total: Decimal = field(init=False)
    cambio: Decimal = field(init=False)

    def __post_init__(self) -> None:
        if not self.detalles:
            raise ValueError("La venta debe tener al menos un detalle.")

        suma_detalles = sum(d.subtotal for d in self.detalles)

        if self.descuento < Decimal("0"):
            raise ValueError("El descuento no puede ser negativo.")

        if self.descuento > suma_detalles:
            raise ValueError("El descuento no puede ser mayor que el subtotal.")

        self.subtotal = suma_detalles - self.descuento

        # Calcular impuesto (16% de IVA sobre el subtotal)
        self.impuesto = (self.subtotal * Decimal("0.16")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        self.total = self.subtotal + self.impuesto

        if self.pago_con < self.total:
            raise ValueError(
                f"El pago (${self.pago_con:.2f}) es insuficiente para cubrir "
                f"el total de la venta (${self.total:.2f})."
            )

        self.cambio = (self.pago_con - self.total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


@dataclass
class LogAuditoria:
    fecha_hora: str
    cajero_id: str
    operacion: str  # ANULACION, MODIFICACION_PRECIO, DESCUENTO_ESPECIAL, CIERRE_CAJA
    estado_anterior: str | None
    estado_nuevo: str | None
    detalles: str
    id: int | None = None
