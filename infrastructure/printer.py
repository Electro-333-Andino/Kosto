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
infrastructure/printer.py

Módulo de infraestructura para el manejo de la impresora térmica.
Encapsula los detalles físicos (ancho de papel, puerto, protocolos ESC/POS)
y proporciona una interfaz limpia para la impresión de tickets de venta.
Lanza excepciones específicas de PrinterError ante fallos simulados o reales.
"""


class PrinterError(Exception):
    """
    Excepción personalizada para representar fallos físicos en la impresora térmica:
    - Ausencia de papel
    - Atasco de papel
    - Cable USB desconectado
    - Bloqueo en la cola de impresión
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ThermalPrinter:
    """
    Encapsula la lógica de comunicación física con la impresora térmica (58mm/80mm).
    """

    def __init__(self, ancho_papel: int = 80, puerto: str = "USB001") -> None:
        self.ancho_papel = ancho_papel
        self.puerto = puerto
        # Estado de simulación para pruebas de resiliencia
        self.simular_fallo = False
        self.tipo_fallo = (
            "Sin papel"  # Opciones: "Sin papel", "Atasco de papel", "Desconectada"
        )

    def imprimir_ticket(self, ticket_data: dict) -> str:
        """
        Intenta enviar el comando de impresión a la impresora.
        Si 'simular_fallo' es True, lanza un PrinterError específico
        para verificar la resiliencia.
        Retorna el contenido de texto del ticket impreso en caso de éxito.
        """
        if self.simular_fallo:
            raise PrinterError(
                f"Error de Hardware: {self.tipo_fallo} en el puerto {self.puerto}."
            )

        # Construir formato de ticket para ancho_papel (ej. 80 cols)
        # 80mm suele ser ~48 caracteres, 58mm suele ser ~32 de ancho.
        cols = 48 if self.ancho_papel == 80 else 32

        lineas = []
        lineas.append("=" * cols)
        lineas.append("KOSTO POS - TICKET DE VENTA".center(cols))
        lineas.append("=" * cols)

        lineas.append(f"Fecha: {ticket_data.get('fecha_hora', 'N/A')}")
        lineas.append(f"Cajero: {ticket_data.get('cajero_id', 'N/A')}")
        lineas.append(f"Ticket ID: {ticket_data.get('venta_id', 'N/A')}")
        lineas.append("-" * cols)

        # Detalle de productos
        # Cant.  Descripción          P.Unit   Total
        # Usamos anchos de columnas formateados según el ancho de papel
        if cols == 48:
            header_det = f"{'Cant':<5}{'Descripción':<21}{'P.Unit':<10}{'Total':>12}"
        else:
            header_det = f"{'Cant':<4}{'Descripción':<14}{'P.U.':<6}{'Total':>8}"

        lineas.append(header_det)
        lineas.append("-" * cols)

        for item in ticket_data.get("detalles", []):
            cant = str(item.get("cantidad", 1))
            nombre = item.get("nombre", "")
            p_unit = f"${item.get('precio_unitario', 0.0):.2f}"
            subt = f"${item.get('subtotal', 0.0):.2f}"

            if cols == 48:
                # Cortar nombre a 20 caracteres
                nombre_c = nombre[:20]
                lineas.append(f"{cant:<5}{nombre_c:<21}{p_unit:<10}{subt:>12}")
            else:
                # Cortar nombre a 13 caracteres
                nombre_c = nombre[:13]
                lineas.append(f"{cant:<4}{nombre_c:<14}{p_unit:<6}{subt:>8}")

        lineas.append("-" * cols)
        subtotal_str = f"${ticket_data.get('subtotal', 0.0):.2f}"
        impuesto_str = f"${ticket_data.get('impuesto', 0.0):.2f}"
        descuento_str = f"${ticket_data.get('descuento', 0.0):.2f}"
        total_str = f"${ticket_data.get('total', 0.0):.2f}"
        pago_str = f"${ticket_data.get('pago_con', 0.0):.2f}"
        cambio_str = f"${ticket_data.get('cambio', 0.0):.2f}"

        lineas.append(f"SUBTOTAL:{subtotal_str:>20}".rjust(cols))
        lineas.append(f"DESCUENTO:{descuento_str:>19}".rjust(cols))
        lineas.append(f"IVA (16%):{impuesto_str:>19}".rjust(cols))
        lineas.append(f"TOTAL:{total_str:>23}".rjust(cols))
        lineas.append("-" * cols)
        lineas.append(f"PAGO CON:{pago_str:>20}".rjust(cols))
        lineas.append(f"CAMBIO:{cambio_str:>22}".rjust(cols))
        lineas.append("=" * cols)
        lineas.append("¡Gracias por su preferencia!".center(cols))
        lineas.append("=" * cols)
        lineas.append("\n\n")  # Feed lines

        ticket_text = "\n".join(lineas)

        # Guardar localmente
        try:
            with open("ultimos_tickets.log", "a", encoding="utf-8") as f:
                f.write(ticket_text)
        except Exception:
            pass

        return ticket_text
