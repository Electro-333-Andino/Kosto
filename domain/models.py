"""
domain/models.py

Este módulo contiene el modelo de dominio de Kosto.
Define la entidad core de Producto y maneja todos los cálculos matemáticos y comerciales.
Está completamente desacoplado de bases de datos y de la interfaz de usuario.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Producto:
    nombre: str
    costo_total: float
    unidades_por_paquete: int
    precio_manual: Optional[float] = None
    id: Optional[int] = None

    # Campos calculados automáticamente
    costo_unitario_real: float = field(init=False)
    precio_sugerido: float = field(init=False)
    ganancia_neta: float = field(init=False)

    def __post_init__(self) -> None:
        """
        Valida las propiedades de entrada y calcula automáticamente el costo unitario,
        el precio de venta sugerido y la ganancia neta.
        """
        # Validación de entradas
        if not self.nombre or not self.nombre.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")

        try:
            self.costo_total = float(self.costo_total)
        except (ValueError, TypeError):
            raise ValueError("El costo total debe ser un número válido.")

        try:
            self.unidades_por_paquete = int(self.unidades_por_paquete)
        except (ValueError, TypeError):
            raise ValueError(
                "Las unidades por paquete deben ser un número entero válido."
            )

        if self.costo_total <= 0:
            raise ValueError("El costo total debe ser mayor que cero.")

        if self.unidades_por_paquete <= 0:
            raise ValueError("Las unidades por paquete deben ser mayores que cero.")

        self.nombre = self.nombre.strip()

        # Costo unitario real (ej. 3.67 / 12 = 0.3058)
        self.costo_unitario_real = round(
            self.costo_total / self.unidades_por_paquete, 4
        )

        # Precio de venta sugerido (redondeado, ej. 0.31)
        self.precio_sugerido = round(self.costo_unitario_real, 2)

        # Si el precio manual no está definido, se inicializa con el precio sugerido
        if self.precio_manual is None:
            self.precio_manual = self.precio_sugerido
        else:
            try:
                self.precio_manual = float(self.precio_manual)
            except (ValueError, TypeError):
                raise ValueError("El precio manual debe ser un número válido.")
            if self.precio_manual < 0:
                raise ValueError("El precio manual no puede ser negativo.")

        # Cálculo final: Ganancia neta (Precio manual - Costo unitario real)
        self.recalculate_ganancia()

    def update_precio_manual(self, nuevo_precio: float) -> None:
        """
        Permite actualizar el precio manual de venta y recalcula la ganancia neta.
        """
        try:
            nuevo_precio = float(nuevo_precio)
        except (ValueError, TypeError):
            raise ValueError("El precio manual debe ser un número válido.")

        if nuevo_precio < 0:
            raise ValueError("El precio manual no puede ser negativo.")

        self.precio_manual = nuevo_precio
        self.recalculate_ganancia()

    def recalculate_ganancia(self) -> None:
        """
        Recalcula la ganancia neta por unidad.
        """
        if self.precio_manual is None:
            self.precio_manual = self.precio_sugerido
        self.ganancia_neta = round(self.precio_manual - self.costo_unitario_real, 4)
