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
presentation/gui.py

Este módulo implementa la interfaz gráfica de usuario (GUI) utilizando CustomTkinter.
Sigue estrictamente la paleta de colores de Catppuccin Mocha y una arquitectura limpia.
Divide la aplicación en tres pestañas: Inventario, Terminal POS y Auditoría/Ventas.
Delega toda la lógica de negocio y persistencia en POSUseCase y el dominio.
"""

import tkinter as tk
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from domain.models import Producto, Venta
from domain.use_cases import POSUseCase
from infrastructure.database import DatabaseManager
from infrastructure.printer import ThermalPrinter


class CustomConfirmDialog(ctk.CTkToplevel):  # type: ignore[misc]
    """
    Cuadro de diálogo de confirmación personalizado y modal.
    Adopta completamente el tema oscuro y los colores
    de la paleta Catppuccin Mocha del padre.
    """

    def __init__(self, parent: ctk.CTk, title: str, message: str) -> None:
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.result = False

        # Configuración de comportamiento modal (bloquea el parent)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        # Aplicar fondo de la paleta Catppuccin Mocha
        self.configure(fg_color="#181825")

        # Centrar la ventana de diálogo respecto a la ventana padre
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 175
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
        self.geometry(f"350x180+{x}+{y}")

        # Mensaje del cuadro de diálogo
        self.lbl_msg = ctk.CTkLabel(
            self,
            text=message,
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Arial", size=13),
            wraplength=310,
            justify="center",
        )
        self.lbl_msg.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Contenedor para botones de acción
        self.frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buttons.pack(fill="x", side="bottom", padx=20, pady=(10, 20))

        # Botón para confirmar (Eliminar/Acción)
        self.btn_yes = ctk.CTkButton(
            self.frame_buttons,
            text="Confirmar",
            fg_color="#f38ba8",
            hover_color="#eba0ac",
            text_color="#11111b",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            command=self.on_yes,
        )
        self.btn_yes.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Botón para cancelar
        self.btn_no = ctk.CTkButton(
            self.frame_buttons,
            text="Cancelar",
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            command=self.on_no,
        )
        self.btn_no.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Bloquear el flujo del hilo principal hasta cerrar la ventana
        self.wait_window(self)

    def on_yes(self) -> None:
        self.result = True
        self.destroy()

    def on_no(self) -> None:
        self.result = False
        self.destroy()


class KostoApp(ctk.CTk):  # type: ignore[misc]
    """
    Ventana principal del sistema POS e inventario Kosto.
    """

    def __init__(self, db: DatabaseManager, tickets_log_path: str | None = None):
        super().__init__()
        self.db = db

        # Inicializar impresora e inyectar en Casos de Uso.
        # En producción la ruta del log de tickets apunta a %PROGRAMDATA%\Kosto\logs.
        self.printer = ThermalPrinter(ruta_log=tickets_log_path)
        self.pos_use_case = POSUseCase(self.db, self.printer)

        # Estados de la UI
        self.producto_seleccionado_id: int | None = None
        self._search_timer_id: str | None = None
        self._pos_search_timer_id: str | None = None

        # Estado del Carrito POS (diccionario de id -> cantidad)
        self.carrito: dict[int, int] = {}

        # Última venta procesada (para reintentar impresión en caso de fallo)
        self.ultima_venta_procesada: Venta | None = None

        # Venta seleccionada en el visor de auditoría
        self.venta_seleccionada_id: int | None = None

        # Configuración básica de la ventana
        self.title("KOSTO - Terminal Punto de Venta (POS) e Inventario")
        self.geometry("1250x780")
        self.minsize(1150, 700)

        # Paleta de colores: Catppuccin Mocha
        self.COLOR_BG_PRINCIPAL = "#1e1e2e"
        self.COLOR_BG_SECUNDARIO = "#181825"
        self.COLOR_TEXTO_PRINCIPAL = "#cdd6f4"
        self.COLOR_TEXTO_SECUNDARIO = "#a6adc8"
        self.COLOR_BOTONES = "#89b4fa"
        self.COLOR_BOTONES_HOVER = "#b4befe"
        self.COLOR_INDICADOR_EXITO = "#a6e3a1"
        self.COLOR_INDICADOR_ERROR = "#f38ba8"
        self.COLOR_BORDE = "#313244"
        self.COLOR_WARN = "#f9e2af"

        # Aplicar fondo principal
        self.configure(fg_color=self.COLOR_BG_PRINCIPAL)

        # Crear panel de pestañas
        self.setup_tabs()

        # Cargar datos iniciales
        self.refresh_inventario_list()
        self.refresh_pos_catalog()
        self.refresh_auditoria_tab()

    def report_callback_exception(
        self, exc: type[BaseException], val: BaseException, tb: Any
    ) -> None:
        """
        Manejador global de excepciones no capturadas de los callbacks de Tk.
        Muestra un mensaje limpio en la UI en lugar de crashear o imprimir
        un traceback silencioso en la ventana de consola.
        """
        messagebox.showerror(
            "Error Inesperado",
            "Ocurrió un error inesperado en la aplicación.\n\n"
            f"{type(val).__name__}: {val}",
        )

    def setup_tabs(self) -> None:
        """
        Crea las tres pestañas principales usando CTkTabview.
        """
        self.tabview = ctk.CTkTabview(
            self,
            segmented_button_fg_color=self.COLOR_BG_SECUNDARIO,
            segmented_button_selected_color=self.COLOR_BOTONES,
            segmented_button_selected_hover_color=self.COLOR_BOTONES_HOVER,
            segmented_button_unselected_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tab_inventario = self.tabview.add("Gestión de Inventario")
        self.tab_pos = self.tabview.add("Terminal POS")
        self.tab_auditoria = self.tabview.add("Auditoría de Ventas")

        # Configurar diseños dentro de cada pestaña
        self.setup_tab_inventario()
        self.setup_tab_pos()
        self.setup_tab_auditoria()

    # ==========================================
    # PESTAÑA 1: GESTIÓN DE INVENTARIO
    # ==========================================
    def setup_tab_inventario(self) -> None:
        """
        Crea la interfaz de control de productos de inventario.
        """
        self.tab_inventario.grid_rowconfigure(0, weight=1)
        self.tab_inventario.grid_columnconfigure(0, weight=25)  # Formulario (25%)
        self.tab_inventario.grid_columnconfigure(1, weight=75)  # Tabla (75%)

        # Panel izquierdo: Formulario (Scrollable para visibilidad de botones)
        self.frame_inv_formulario = ctk.CTkScrollableFrame(
            self.tab_inventario,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=12,
        )
        self.frame_inv_formulario.grid(
            row=0, column=0, sticky="nsew", padx=(5, 7), pady=5
        )
        self.setup_formulario_inventario()

        # Panel derecho: Tabla de productos
        self.frame_inv_tabla = ctk.CTkFrame(
            self.tab_inventario, fg_color=self.COLOR_BG_PRINCIPAL
        )
        self.frame_inv_tabla.grid(row=0, column=1, sticky="nsew", padx=(7, 5), pady=5)
        self.setup_tabla_inventario()

    def setup_formulario_inventario(self) -> None:
        self.frame_inv_formulario.grid_columnconfigure(0, weight=1)

        # Título del Formulario
        self.lbl_form_title = ctk.CTkLabel(
            self.frame_inv_formulario,
            text="REGISTRAR PRODUCTO",
            font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_form_title.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        # Campo: Nombre del Producto
        self.lbl_nombre = ctk.CTkLabel(
            self.frame_inv_formulario,
            text="Nombre del Producto:",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_nombre.grid(row=1, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_nombre = ctk.CTkEntry(
            self.frame_inv_formulario,
            placeholder_text="Ej. Aceite de Oliva",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=32,
        )
        self.entry_nombre.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.entry_nombre.bind("<KeyRelease>", lambda e: self.recalcular_form())

        # Campo: Costo Total del Paquete
        self.lbl_costo_total = ctk.CTkLabel(
            self.frame_inv_formulario,
            text="Costo Total del Paquete ($):",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_costo_total.grid(row=3, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_costo_total = ctk.CTkEntry(
            self.frame_inv_formulario,
            placeholder_text="Ej. 3.67",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=32,
        )
        self.entry_costo_total.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.entry_costo_total.bind("<KeyRelease>", lambda e: self.recalcular_form())

        # Campo: Unidades por Paquete
        self.lbl_unidades = ctk.CTkLabel(
            self.frame_inv_formulario,
            text="Unidades por Paquete:",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_unidades.grid(row=5, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_unidades = ctk.CTkEntry(
            self.frame_inv_formulario,
            placeholder_text="Ej. 12",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=32,
        )
        self.entry_unidades.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.entry_unidades.bind("<KeyRelease>", lambda e: self.recalcular_form())

        # Campo: Stock (Cantidad Disponible) - REQUISITO POS CORE
        self.lbl_stock = ctk.CTkLabel(
            self.frame_inv_formulario,
            text="Stock (Unidades en Inventario):",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_stock.grid(row=7, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_stock = ctk.CTkEntry(
            self.frame_inv_formulario,
            placeholder_text="Ej. 100",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=32,
        )
        self.entry_stock.grid(row=8, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.entry_stock.insert(0, "0")

        # Separador / Cálculos rápidos
        self.frame_calculos = ctk.CTkFrame(
            self.frame_inv_formulario,
            fg_color=self.COLOR_BG_PRINCIPAL,
            corner_radius=8,
            border_color=self.COLOR_BORDE,
            border_width=1,
        )
        self.frame_calculos.grid(row=9, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.frame_calculos.grid_columnconfigure((0, 1), weight=1)

        self.lbl_costo_unitario = ctk.CTkLabel(
            self.frame_calculos,
            text="Costo Unit. Real:",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_costo_unitario.grid(row=0, column=0, padx=12, pady=(8, 2), sticky="w")

        self.lbl_costo_unitario_val = ctk.CTkLabel(
            self.frame_calculos,
            text="$0.0000",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_costo_unitario_val.grid(
            row=0, column=1, padx=12, pady=(8, 2), sticky="e"
        )

        self.lbl_precio_sugerido = ctk.CTkLabel(
            self.frame_calculos,
            text="Precio Sugerido:",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_precio_sugerido.grid(row=1, column=0, padx=12, pady=5, sticky="w")

        self.lbl_precio_sugerido_val = ctk.CTkLabel(
            self.frame_calculos,
            text="$0.00",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_precio_sugerido_val.grid(row=1, column=1, padx=12, pady=5, sticky="e")

        # Campo: Precio de Venta Manual
        self.lbl_precio_manual = ctk.CTkLabel(
            self.frame_inv_formulario,
            text="Precio de Venta Manual ($):",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_precio_manual.grid(row=10, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_precio_manual = ctk.CTkEntry(
            self.frame_inv_formulario,
            placeholder_text="Dejar vacío para usar el sugerido",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=32,
        )
        self.entry_precio_manual.grid(
            row=11, column=0, padx=20, pady=(0, 10), sticky="ew"
        )
        self.entry_precio_manual.bind(
            "<KeyRelease>", lambda e: self.recalcular_form(manual_override=True)
        )

        # Ganancia Destacada
        self.frame_ganancia = ctk.CTkFrame(
            self.frame_inv_formulario,
            fg_color=self.COLOR_BG_PRINCIPAL,
            corner_radius=8,
            border_color=self.COLOR_BORDE,
            border_width=1,
        )
        self.frame_ganancia.grid(row=12, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.frame_ganancia.grid_columnconfigure((0, 1), weight=1)

        self.lbl_ganancia = ctk.CTkLabel(
            self.frame_ganancia,
            text="Ganancia por Unidad:",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_ganancia.grid(row=0, column=0, padx=12, pady=8, sticky="w")

        self.lbl_ganancia_val = ctk.CTkLabel(
            self.frame_ganancia,
            text="$0.0000",
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            text_color=self.COLOR_INDICADOR_EXITO,
        )
        self.lbl_ganancia_val.grid(row=0, column=1, padx=12, pady=8, sticky="e")

        # Logs / Estado
        self.lbl_status = ctk.CTkLabel(
            self.frame_inv_formulario,
            text="",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_INDICADOR_EXITO,
            wraplength=280,
        )
        self.lbl_status.grid(row=13, column=0, padx=20, pady=(0, 5), sticky="ew")

        # Botones del formulario
        self.frame_botones_form = ctk.CTkFrame(
            self.frame_inv_formulario, fg_color="transparent"
        )
        self.frame_botones_form.grid(
            row=14, column=0, padx=20, pady=(5, 15), sticky="ew"
        )
        self.frame_botones_form.grid_columnconfigure((0, 1), weight=1)

        self.btn_guardar = ctk.CTkButton(
            self.frame_botones_form,
            text="Guardar",
            fg_color=self.COLOR_BOTONES,
            hover_color=self.COLOR_BOTONES_HOVER,
            text_color="#11111b",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            height=35,
            command=self.guardar_producto_inventario,
        )
        self.btn_guardar.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_limpiar = ctk.CTkButton(
            self.frame_botones_form,
            text="Limpiar",
            fg_color=self.COLOR_BORDE,
            hover_color="#45475a",
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            height=35,
            command=self.limpiar_formulario_inventario,
        )
        self.btn_limpiar.grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def setup_tabla_inventario(self) -> None:
        self.frame_inv_tabla.grid_columnconfigure(0, weight=1)
        self.frame_inv_tabla.grid_rowconfigure(2, weight=1)

        # Buscador
        self.frame_buscador = ctk.CTkFrame(self.frame_inv_tabla, fg_color="transparent")
        self.frame_buscador.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.frame_buscador.grid_columnconfigure(1, weight=1)

        self.lbl_buscar = ctk.CTkLabel(
            self.frame_buscador,
            text="Buscar:",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_buscar.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.entry_buscar = ctk.CTkEntry(
            self.frame_buscador,
            placeholder_text="Escribe el nombre de un producto para buscar...",
            fg_color=self.COLOR_BG_SECUNDARIO,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=32,
        )
        self.entry_buscar.grid(row=0, column=1, sticky="ew")
        self.entry_buscar.bind("<KeyRelease>", self.al_escribir_busqueda_inventario)

        self.btn_limpiar_buscar = ctk.CTkButton(
            self.frame_buscador,
            text="Limpiar Filtro",
            fg_color=self.COLOR_BORDE,
            hover_color="#45475a",
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            width=90,
            height=32,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            command=self.limpiar_busqueda_inventario,
        )
        self.btn_limpiar_buscar.grid(row=0, column=2, padx=(8, 0))

        # Cabecera de tabla
        self.frame_headers = ctk.CTkFrame(
            self.frame_inv_tabla,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
            height=36,
        )
        self.frame_headers.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        self.column_weights = [3.5, 1.5, 1.0, 1.5, 1.5, 1.5, 1.2, 1.8, 2.5]
        for idx, w in enumerate(self.column_weights):
            self.frame_headers.grid_columnconfigure(
                idx, weight=int(w * 10), uniform="inv_table_col"
            )

        headers = [
            "Nombre",
            "Cost. Paq",
            "Unids",
            "Cost. Unit",
            "P. Sugerido",
            "P. Venta",
            "Stock",
            "Ganancia Unit",
            "Acciones",
        ]

        for idx, text in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.frame_headers,
                text=text,
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center" if idx > 0 else "w",
            )
            padx_lbl = (12, 5) if idx == 0 else 5
            lbl.grid(
                row=0,
                column=idx,
                padx=padx_lbl,
                pady=8,
                sticky="ew" if idx > 0 else "w",
            )

        # Contenedor scrollable
        self.scroll_table = ctk.CTkScrollableFrame(
            self.frame_inv_tabla,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
        )
        self.scroll_table.grid(row=2, column=0, sticky="nsew")
        self.scroll_table.grid_columnconfigure(0, weight=1)

    def al_escribir_busqueda_inventario(self, event: tk.Event) -> None:
        if self._search_timer_id is not None:
            self.after_cancel(self._search_timer_id)
        self._search_timer_id = self.after(300, self.refresh_inventario_list)

    def recalcular_form(self, manual_override: bool = False) -> None:
        nombre = self.entry_nombre.get().strip()
        costo_total_raw = self.entry_costo_total.get().strip()
        unidades_raw = self.entry_unidades.get().strip()
        precio_manual_raw = self.entry_precio_manual.get().strip()

        self.lbl_status.configure(text="")

        if not nombre or not costo_total_raw or not unidades_raw:
            self.lbl_costo_unitario_val.configure(text="$0.0000")
            self.lbl_precio_sugerido_val.configure(text="$0.00")
            self.lbl_ganancia_val.configure(
                text="$0.0000", text_color=self.COLOR_INDICADOR_EXITO
            )
            return

        try:
            costo_total = Decimal(costo_total_raw.replace(",", "."))
            unidades = int(unidades_raw)

            if costo_total <= Decimal("0") or unidades <= 0:
                raise ValueError()
        except (ValueError, InvalidOperation):
            self.lbl_costo_unitario_val.configure(
                text="Inválido", text_color=self.COLOR_INDICADOR_ERROR
            )
            self.lbl_precio_sugerido_val.configure(
                text="Inválido", text_color=self.COLOR_INDICADOR_ERROR
            )
            self.lbl_ganancia_val.configure(
                text="Inválido", text_color=self.COLOR_INDICADOR_ERROR
            )
            return

        self.lbl_costo_unitario_val.configure(text_color=self.COLOR_TEXTO_PRINCIPAL)
        self.lbl_precio_sugerido_val.configure(text_color=self.COLOR_TEXTO_PRINCIPAL)

        try:
            p_manual = None
            if precio_manual_raw:
                try:
                    p_manual = Decimal(precio_manual_raw.replace(",", "."))
                except InvalidOperation:
                    pass

            prod_temp = Producto(
                nombre=nombre,
                costo_total=costo_total,
                unidades_por_paquete=unidades,
                precio_manual=p_manual,
            )

            if not manual_override and not precio_manual_raw:
                self.entry_precio_manual.delete(0, tk.END)
                self.entry_precio_manual.insert(0, f"{prod_temp.precio_sugerido:.2f}")
                prod_temp.update_precio_manual(prod_temp.precio_sugerido)

            self.lbl_costo_unitario_val.configure(
                text=f"${prod_temp.costo_unitario_real:.4f}"
            )
            self.lbl_precio_sugerido_val.configure(
                text=f"${prod_temp.precio_sugerido:.2f}"
            )
            self.lbl_ganancia_val.configure(text=f"${prod_temp.ganancia_neta:.4f}")

            if prod_temp.ganancia_neta >= Decimal("0"):
                self.lbl_ganancia_val.configure(text_color=self.COLOR_INDICADOR_EXITO)
            else:
                self.lbl_ganancia_val.configure(text_color=self.COLOR_INDICADOR_ERROR)

        except ValueError:
            self.lbl_ganancia_val.configure(
                text="Error Calc.", text_color=self.COLOR_INDICADOR_ERROR
            )

    def guardar_producto_inventario(self) -> None:
        nombre = self.entry_nombre.get().strip()
        costo_total_raw = self.entry_costo_total.get().strip()
        unidades_raw = self.entry_unidades.get().strip()
        stock_raw = self.entry_stock.get().strip()
        precio_manual_raw = self.entry_precio_manual.get().strip()

        # Sanitización y validaciones de capa de presentación (Zero Trust)
        if not nombre:
            self.show_status("El nombre del producto es requerido.", es_error=True)
            return

        if len(nombre) > 100:
            self.show_status(
                "El nombre no puede exceder los 100 caracteres.", es_error=True
            )
            return

        try:
            costo_total = Decimal(costo_total_raw.replace(",", "."))
        except InvalidOperation:
            self.show_status(
                "El costo del paquete debe ser un número válido.", es_error=True
            )
            return

        try:
            unidades = int(unidades_raw)
        except ValueError:
            self.show_status(
                "Las unidades por paquete deben ser un número entero.",
                es_error=True,
            )
            return

        try:
            stock = int(stock_raw)
            if stock < 0:
                raise ValueError()
        except ValueError:
            self.show_status(
                "El stock debe ser un número entero mayor o igual a cero.",
                es_error=True,
            )
            return

        precio_manual = None
        if precio_manual_raw:
            try:
                precio_manual = Decimal(precio_manual_raw.replace(",", "."))
            except InvalidOperation:
                self.show_status(
                    "El precio de venta manual debe ser un número válido.",
                    es_error=True,
                )
                return

        # Intentar crear entidad y persistir con auditoría
        try:
            if self.producto_seleccionado_id is None:
                producto = Producto(
                    nombre=nombre,
                    costo_total=costo_total,
                    unidades_por_paquete=unidades,
                    precio_manual=precio_manual,
                    stock=stock,
                )
                self.db.insertar_producto(producto)
                self.show_status(
                    f"¡'{producto.nombre}' registrado con éxito!", es_error=False
                )
                self.limpiar_formulario_inventario()
            else:
                # Usar POSUseCase para guardar cambio de precio y
                # auditar automáticamente si cambia
                # O guardar el producto con auditoría si corresponde.
                # Para simplificar y mantener Clean Architecture:
                cajero = "SISTEMA"
                self.pos_use_case.modificar_precio_manual_con_auditoria(
                    self.producto_seleccionado_id,
                    precio_manual if precio_manual is not None else Decimal("0.00"),
                    cajero,
                )

                # También actualizar los otros campos básicos
                prod_existente = self.db.obtener_producto_por_id(
                    self.producto_seleccionado_id
                )
                if prod_existente:
                    prod_existente.nombre = nombre
                    prod_existente.costo_total = costo_total
                    prod_existente.unidades_por_paquete = unidades
                    prod_existente.stock = stock
                    # Validar nuevamente
                    prod_existente.__post_init__()
                    self.db.actualizar_producto(prod_existente)

                self.show_status(
                    f"¡'{nombre}' actualizado con éxito y auditado!",
                    es_error=False,
                )
                self.limpiar_formulario_inventario()

        except ValueError as err:
            self.show_status(str(err), es_error=True)
            return
        except Exception as e:
            self.show_status(f"Error inesperado: {str(e)}", es_error=True)
            return

        self.refresh_inventario_list()
        self.refresh_pos_catalog()

    def refresh_inventario_list(self) -> None:
        for widget in self.scroll_table.winfo_children():
            widget.destroy()

        busqueda = self.entry_buscar.get().strip()

        try:
            productos = self.db.obtener_productos(busqueda=busqueda)
        except Exception as e:
            lbl_error = ctk.CTkLabel(
                self.scroll_table,
                text=f"Error al cargar base de datos: {str(e)}",
                text_color=self.COLOR_INDICADOR_ERROR,
            )
            lbl_error.pack(pady=20)
            return

        if not productos:
            lbl_vacio = ctk.CTkLabel(
                self.scroll_table,
                text="No se encontraron productos en el inventario.",
                font=ctk.CTkFont(family="Arial", size=13, slant="italic"),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
            )
            lbl_vacio.pack(pady=40)
            return

        for idx, prod in enumerate(productos):
            bg_fila = self.COLOR_BG_SECUNDARIO if idx % 2 == 0 else "#212130"

            row_frame = ctk.CTkFrame(
                self.scroll_table, fg_color=bg_fila, height=40, corner_radius=6
            )
            row_frame.pack(fill="x", pady=2, padx=2)

            for c_idx, w in enumerate(self.column_weights):
                row_frame.grid_columnconfigure(
                    c_idx, weight=int(w * 10), uniform="inv_table_col"
                )

            lbl_nom = ctk.CTkLabel(
                row_frame,
                text=prod.nombre,
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="w",
            )
            lbl_nom.grid(row=0, column=0, padx=(12, 5), pady=6, sticky="w")

            lbl_costo_p = ctk.CTkLabel(
                row_frame,
                text=f"${prod.costo_total:.2f}",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center",
            )
            lbl_costo_p.grid(row=0, column=1, padx=2, pady=6, sticky="ew")

            lbl_unid = ctk.CTkLabel(
                row_frame,
                text=str(prod.unidades_por_paquete),
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center",
            )
            lbl_unid.grid(row=0, column=2, padx=2, pady=6, sticky="ew")

            lbl_costo_u = ctk.CTkLabel(
                row_frame,
                text=f"${prod.costo_unitario_real:.4f}",
                font=ctk.CTkFont(family="Arial", size=10),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
                anchor="center",
            )
            lbl_costo_u.grid(row=0, column=3, padx=2, pady=6, sticky="ew")

            lbl_sug = ctk.CTkLabel(
                row_frame,
                text=f"${prod.precio_sugerido:.2f}",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
                anchor="center",
            )
            lbl_sug.grid(row=0, column=4, padx=2, pady=6, sticky="ew")

            lbl_man = ctk.CTkLabel(
                row_frame,
                text=f"${prod.precio_manual:.2f}",
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=self.COLOR_BOTONES,
                anchor="center",
            )
            lbl_man.grid(row=0, column=5, padx=2, pady=6, sticky="ew")

            # Stock físico column
            color_stock = (
                self.COLOR_INDICADOR_EXITO
                if prod.stock > 10
                else (self.COLOR_WARN if prod.stock > 0 else self.COLOR_INDICADOR_ERROR)
            )
            lbl_stk = ctk.CTkLabel(
                row_frame,
                text=str(prod.stock),
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=color_stock,
                anchor="center",
            )
            lbl_stk.grid(row=0, column=6, padx=2, pady=6, sticky="ew")

            # Ganancia
            color_ganancia = (
                self.COLOR_INDICADOR_EXITO
                if prod.ganancia_neta >= Decimal("0")
                else self.COLOR_INDICADOR_ERROR
            )
            lbl_gan = ctk.CTkLabel(
                row_frame,
                text=f"${prod.ganancia_neta:.4f}",
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=color_ganancia,
                anchor="center",
            )
            lbl_gan.grid(row=0, column=7, padx=2, pady=6, sticky="ew")

            # Acciones
            frame_acciones = ctk.CTkFrame(row_frame, fg_color="transparent")
            frame_acciones.grid(row=0, column=8, padx=(5, 12), pady=2, sticky="e")

            btn_edit = ctk.CTkButton(
                frame_acciones,
                text="✎",
                fg_color=self.COLOR_BOTONES,
                hover_color=self.COLOR_BOTONES_HOVER,
                text_color="#11111b",
                width=26,
                height=22,
                font=ctk.CTkFont(family="Arial", size=11),
                command=lambda p=prod: self.cargar_producto_inventario_edicion(p),
            )
            btn_edit.pack(side="left", padx=1)

            btn_delete = ctk.CTkButton(
                frame_acciones,
                text="🗑",
                fg_color=self.COLOR_INDICADOR_ERROR,
                hover_color="#eba0ac",
                text_color="#11111b",
                width=26,
                height=22,
                font=ctk.CTkFont(family="Arial", size=11),
                command=lambda p=prod: self.confirmar_eliminar_inventario(p),
            )
            btn_delete.pack(side="left", padx=1)

    def cargar_producto_inventario_edicion(self, producto: Producto) -> None:
        self.producto_seleccionado_id = producto.id

        self.entry_nombre.delete(0, tk.END)
        self.entry_nombre.insert(0, producto.nombre)

        self.entry_costo_total.delete(0, tk.END)
        self.entry_costo_total.insert(0, f"{producto.costo_total:.2f}")

        self.entry_unidades.delete(0, tk.END)
        self.entry_unidades.insert(0, str(producto.unidades_por_paquete))

        self.entry_stock.delete(0, tk.END)
        self.entry_stock.insert(0, str(producto.stock))

        self.entry_precio_manual.delete(0, tk.END)
        self.entry_precio_manual.insert(0, f"{producto.precio_manual:.2f}")

        self.lbl_form_title.configure(
            text=f"EDITAR PRODUCTO (ID: {producto.id})", text_color=self.COLOR_BOTONES
        )
        self.btn_guardar.configure(
            text="Guardar Cambios",
            fg_color=self.COLOR_INDICADOR_EXITO,
            hover_color="#c2f2bd",
        )

        self.recalcular_form(manual_override=True)
        self.show_status(
            "Modifica los campos y haz clic en 'Guardar Cambios'.",
            es_error=False,
        )

    def confirmar_eliminar_inventario(self, producto: Producto) -> None:
        if producto.id is None:
            return

        dialog = CustomConfirmDialog(
            self,
            title="Confirmar eliminación",
            message=(
                f"¿Está seguro de que desea eliminar '{producto.nombre}'?\n"
                "Esta acción no se puede deshacer."
            ),
        )

        if dialog.result:
            try:
                self.db.eliminar_producto(producto.id)
                self.show_status(
                    f"Producto '{producto.nombre}' eliminado con éxito.",
                    es_error=False,
                )

                if self.producto_seleccionado_id == producto.id:
                    self.limpiar_formulario_inventario()

                self.refresh_inventario_list()
                self.refresh_pos_catalog()
            except Exception as e:
                self.show_status(f"Error al eliminar: {str(e)}", es_error=True)

    def limpiar_formulario_inventario(self) -> None:
        self.producto_seleccionado_id = None

        self.entry_nombre.delete(0, tk.END)
        self.entry_costo_total.delete(0, tk.END)
        self.entry_unidades.delete(0, tk.END)
        self.entry_stock.delete(0, tk.END)
        self.entry_stock.insert(0, "0")
        self.entry_precio_manual.delete(0, tk.END)

        self.lbl_costo_unitario_val.configure(
            text="$0.0000", text_color=self.COLOR_TEXTO_PRINCIPAL
        )
        self.lbl_precio_sugerido_val.configure(
            text="$0.00", text_color=self.COLOR_TEXTO_PRINCIPAL
        )
        self.lbl_ganancia_val.configure(
            text="$0.0000", text_color=self.COLOR_INDICADOR_EXITO
        )

        self.lbl_form_title.configure(
            text="REGISTRAR PRODUCTO", text_color=self.COLOR_TEXTO_PRINCIPAL
        )
        self.btn_guardar.configure(
            text="Guardar",
            fg_color=self.COLOR_BOTONES,
            hover_color=self.COLOR_BOTONES_HOVER,
        )

    def limpiar_busqueda_inventario(self) -> None:
        self.entry_buscar.delete(0, tk.END)
        self.refresh_inventario_list()

    def show_status(self, message: str, es_error: bool = False) -> None:
        color = self.COLOR_INDICADOR_ERROR if es_error else self.COLOR_INDICADOR_EXITO
        self.lbl_status.configure(text=message, text_color=color)

    # ==========================================
    # PESTAÑA 2: TERMINAL POS (VENTAS)
    # ==========================================
    def setup_tab_pos(self) -> None:
        """
        Crea la terminal de punto de venta (POS).
        """
        self.tab_pos.grid_rowconfigure(0, weight=1)
        self.tab_pos.grid_columnconfigure(0, weight=5)  # Carrito y Cobro (50%)
        self.tab_pos.grid_columnconfigure(1, weight=5)  # Buscador de productos (50%)

        # Panel izquierdo: Carrito y Controles de pago
        self.frame_pos_carrito = ctk.CTkFrame(
            self.tab_pos,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=12,
        )
        self.frame_pos_carrito.grid(row=0, column=0, sticky="nsew", padx=(5, 5), pady=5)
        self.setup_carrito_pos()

        # Panel derecho: Catálogo/Búsqueda de productos
        self.frame_pos_catalogo = ctk.CTkFrame(
            self.tab_pos, fg_color=self.COLOR_BG_PRINCIPAL
        )
        self.frame_pos_catalogo.grid(
            row=0, column=1, sticky="nsew", padx=(5, 5), pady=5
        )
        self.setup_catalogo_pos()

    def setup_carrito_pos(self) -> None:
        self.frame_pos_carrito.grid_columnconfigure(0, weight=1)
        self.frame_pos_carrito.grid_rowconfigure(2, weight=1)

        # Encabezado del Carrito
        self.lbl_cart_title = ctk.CTkLabel(
            self.frame_pos_carrito,
            text="CARRITO DE COMPRA",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_cart_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        # Cabecera de columnas de carrito
        self.frame_cart_headers = ctk.CTkFrame(
            self.frame_pos_carrito, fg_color="#1e1e2f", height=30
        )
        self.frame_cart_headers.grid(row=1, column=0, sticky="ew", padx=15, pady=2)

        self.cart_weights = [4, 2, 2, 2]
        for idx, w in enumerate(self.cart_weights):
            self.frame_cart_headers.grid_columnconfigure(
                idx, weight=w, uniform="cart_col"
            )

        cart_headers = ["Descripción", "Precio", "Cantidad", "Total"]
        for idx, t in enumerate(cart_headers):
            lbl = ctk.CTkLabel(
                self.frame_cart_headers,
                text=t,
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
                anchor="center" if idx > 0 else "w",
            )
            lbl.grid(
                row=0,
                column=idx,
                padx=5 if idx > 0 else 10,
                pady=5,
                sticky="ew" if idx > 0 else "w",
            )

        # Lista de Items con Scroll
        self.scroll_carrito = ctk.CTkScrollableFrame(
            self.frame_pos_carrito, fg_color="#181825"
        )
        self.scroll_carrito.grid(row=2, column=0, sticky="nsew", padx=15, pady=2)
        self.scroll_carrito.grid_columnconfigure(0, weight=1)

        # Panel inferior de Pago y Sumatorias
        self.frame_checkout = ctk.CTkFrame(
            self.frame_pos_carrito, fg_color="#11111b", corner_radius=10
        )
        self.frame_checkout.grid(row=3, column=0, sticky="ew", padx=15, pady=15)
        self.frame_checkout.grid_columnconfigure((0, 1), weight=1)

        # Inputs de Checkout (Cajero, Descuento, Pago)
        self.frame_checkout_inputs = ctk.CTkFrame(
            self.frame_checkout, fg_color="transparent"
        )
        self.frame_checkout_inputs.grid(
            row=0, column=0, padx=15, pady=15, sticky="nsew"
        )
        self.frame_checkout_inputs.grid_columnconfigure(1, weight=1)

        # Cajero ID
        lbl_cajero_lbl = ctk.CTkLabel(
            self.frame_checkout_inputs,
            text="ID Cajero:",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        lbl_cajero_lbl.grid(row=0, column=0, padx=(0, 5), pady=4, sticky="w")

        self.entry_cajero_id = ctk.CTkEntry(
            self.frame_checkout_inputs,
            placeholder_text="Alfanumérico",
            fg_color="#181825",
            border_color=self.COLOR_BORDE,
            height=28,
            width=120,
        )
        self.entry_cajero_id.grid(row=0, column=1, pady=4, sticky="ew")
        self.entry_cajero_id.insert(0, "CAJERO-01")

        # Descuento Especial
        lbl_desc_lbl = ctk.CTkLabel(
            self.frame_checkout_inputs,
            text="Desc. Especial ($):",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        lbl_desc_lbl.grid(row=1, column=0, padx=(0, 5), pady=4, sticky="w")

        self.entry_pos_descuento = ctk.CTkEntry(
            self.frame_checkout_inputs,
            placeholder_text="0.00",
            fg_color="#181825",
            border_color=self.COLOR_BORDE,
            height=28,
        )
        self.entry_pos_descuento.grid(row=1, column=1, pady=4, sticky="ew")
        self.entry_pos_descuento.insert(0, "0.00")
        self.entry_pos_descuento.bind(
            "<KeyRelease>", lambda e: self.recalcular_totales_pos()
        )

        # Pago con
        lbl_pago_lbl = ctk.CTkLabel(
            self.frame_checkout_inputs,
            text="Efectivo Recibido ($):",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        lbl_pago_lbl.grid(row=2, column=0, padx=(0, 5), pady=4, sticky="w")

        self.entry_pos_pago_con = ctk.CTkEntry(
            self.frame_checkout_inputs,
            placeholder_text="Total o más",
            fg_color="#181825",
            border_color=self.COLOR_BORDE,
            height=28,
        )
        self.entry_pos_pago_con.grid(row=2, column=1, pady=4, sticky="ew")
        self.entry_pos_pago_con.bind(
            "<KeyRelease>", lambda e: self.recalcular_totales_pos()
        )

        # Toggles impresora
        self.cb_simular_fallo_impresora = ctk.CTkCheckBox(
            self.frame_checkout_inputs,
            text="Simular Fallo de Impresora",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
            checkbox_width=16,
            checkbox_height=16,
            corner_radius=4,
            command=self.on_toggle_fallo_impresora,
        )
        self.cb_simular_fallo_impresora.grid(
            row=3, column=0, columnspan=2, pady=(10, 0), sticky="w"
        )

        # Panel de Totales
        self.frame_checkout_totales = ctk.CTkFrame(
            self.frame_checkout, fg_color="transparent"
        )
        self.frame_checkout_totales.grid(
            row=0, column=1, padx=15, pady=15, sticky="nsew"
        )
        self.frame_checkout_totales.grid_columnconfigure(1, weight=1)

        totales_labels = [
            ("Subtotal:", "lbl_pos_subtotal", "$0.00"),
            ("Descuento:", "lbl_pos_descuento_lbl", "$0.00"),
            ("IVA (16%):", "lbl_pos_iva", "$0.00"),
            ("TOTAL A PAGAR:", "lbl_pos_total", "$0.00"),
            ("Cambio/Vuelto:", "lbl_pos_cambio", "$0.00"),
        ]

        for idx, (label_text, attr_name, default_val) in enumerate(totales_labels):
            lbl_l = ctk.CTkLabel(
                self.frame_checkout_totales,
                text=label_text,
                font=ctk.CTkFont(
                    family="Arial",
                    size=12 if idx < 3 else 13,
                    weight="bold" if idx >= 3 else "normal",
                ),
                text_color=(
                    self.COLOR_TEXTO_SECUNDARIO
                    if idx < 3
                    else (
                        self.COLOR_BOTONES if idx == 3 else self.COLOR_INDICADOR_EXITO
                    )
                ),
            )
            lbl_l.grid(row=idx, column=0, pady=2, sticky="w")

            lbl_v = ctk.CTkLabel(
                self.frame_checkout_totales,
                text=default_val,
                font=ctk.CTkFont(
                    family="Arial",
                    size=12 if idx < 3 else 14,
                    weight="bold",
                ),
                text_color=(
                    self.COLOR_TEXTO_PRINCIPAL
                    if idx < 3
                    else (
                        self.COLOR_BOTONES if idx == 3 else self.COLOR_INDICADOR_EXITO
                    )
                ),
            )
            lbl_v.grid(row=idx, column=1, pady=2, sticky="e")
            setattr(self, attr_name, lbl_v)

        # Estado del Cobro
        self.lbl_pos_status = ctk.CTkLabel(
            self.frame_pos_carrito,
            text="",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            wraplength=450,
        )
        self.lbl_pos_status.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="ew")

        # Botones de Acción POS
        self.frame_botones_pos = ctk.CTkFrame(
            self.frame_pos_carrito, fg_color="transparent"
        )
        self.frame_botones_pos.grid(row=5, column=0, padx=15, pady=(5, 15), sticky="ew")
        self.frame_botones_pos.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_cobrar = ctk.CTkButton(
            self.frame_botones_pos,
            text="PROCESAR COBRO",
            fg_color=self.COLOR_INDICADOR_EXITO,
            hover_color="#8cdb85",
            text_color="#11111b",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            height=38,
            command=self.procesar_cobro_pos,
        )
        self.btn_cobrar.grid(row=0, column=0, padx=(0, 3), sticky="ew")

        self.btn_retry_print = ctk.CTkButton(
            self.frame_botones_pos,
            text="REINTENTAR IMPRESIÓN",
            fg_color=self.COLOR_INDICADOR_ERROR,
            hover_color="#eba0ac",
            text_color="#11111b",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            height=38,
            command=self.reintentar_impresion_pos,
        )
        self.btn_retry_print.grid(row=0, column=1, padx=3, sticky="ew")
        self.btn_retry_print.grid_remove()  # Hidden initially

        self.btn_limpiar_carrito = ctk.CTkButton(
            self.frame_botones_pos,
            text="VACIAR CARRITO",
            fg_color=self.COLOR_BORDE,
            hover_color="#45475a",
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            height=38,
            command=self.vaciar_carrito,
        )
        self.btn_limpiar_carrito.grid(row=0, column=2, padx=(3, 0), sticky="ew")

    def setup_catalogo_pos(self) -> None:
        self.frame_pos_catalogo.grid_columnconfigure(0, weight=1)
        self.frame_pos_catalogo.grid_rowconfigure(2, weight=1)

        # Buscador Catalogo
        self.frame_pos_buscador = ctk.CTkFrame(
            self.frame_pos_catalogo, fg_color="transparent"
        )
        self.frame_pos_buscador.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.frame_pos_buscador.grid_columnconfigure(1, weight=1)

        self.lbl_pos_buscar_lbl = ctk.CTkLabel(
            self.frame_pos_buscador,
            text="Filtrar Catálogo:",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_pos_buscar_lbl.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.entry_pos_buscar = ctk.CTkEntry(
            self.frame_pos_buscador,
            placeholder_text="Busque un producto para agregar...",
            fg_color=self.COLOR_BG_SECUNDARIO,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=32,
        )
        self.entry_pos_buscar.grid(row=0, column=1, sticky="ew")
        self.entry_pos_buscar.bind("<KeyRelease>", self.al_escribir_busqueda_pos)

        self.btn_pos_limpiar_buscar = ctk.CTkButton(
            self.frame_pos_buscador,
            text="Limpiar",
            fg_color=self.COLOR_BORDE,
            hover_color="#45475a",
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            width=80,
            height=32,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            command=self.limpiar_busqueda_pos,
        )
        self.btn_pos_limpiar_buscar.grid(row=0, column=2, padx=(8, 0))

        # Headers de Catalogo
        self.frame_pos_headers = ctk.CTkFrame(
            self.frame_pos_catalogo,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
            height=34,
        )
        self.frame_pos_headers.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        self.cat_col_weights = [5, 3, 2, 3]
        for idx, w in enumerate(self.cat_col_weights):
            self.frame_pos_headers.grid_columnconfigure(
                idx, weight=w, uniform="cat_table_col"
            )

        cat_headers = ["Producto", "Precio Unitario", "Disponible", "Acción"]
        for idx, text in enumerate(cat_headers):
            lbl = ctk.CTkLabel(
                self.frame_pos_headers,
                text=text,
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center" if idx > 0 else "w",
            )
            padx_lbl = (12, 5) if idx == 0 else 5
            lbl.grid(
                row=0,
                column=idx,
                padx=padx_lbl,
                pady=6,
                sticky="ew" if idx > 0 else "w",
            )

        # Scroll Catalog Frame
        self.scroll_pos_catalog = ctk.CTkScrollableFrame(
            self.frame_pos_catalogo,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
        )
        self.scroll_pos_catalog.grid(row=2, column=0, sticky="nsew")
        self.scroll_pos_catalog.grid_columnconfigure(0, weight=1)

    def al_escribir_busqueda_pos(self, event: tk.Event) -> None:
        if self._pos_search_timer_id is not None:
            self.after_cancel(self._pos_search_timer_id)
        self._pos_search_timer_id = self.after(300, self.refresh_pos_catalog)

    def limpiar_busqueda_pos(self) -> None:
        self.entry_pos_buscar.delete(0, tk.END)
        self.refresh_pos_catalog()

    def on_toggle_fallo_impresora(self) -> None:
        self.printer.simular_fallo = self.cb_simular_fallo_impresora.get()

    def refresh_pos_catalog(self) -> None:
        for widget in self.scroll_pos_catalog.winfo_children():
            widget.destroy()

        busqueda = self.entry_pos_buscar.get().strip()

        try:
            productos = self.db.obtener_productos(busqueda=busqueda)
        except Exception:
            return

        if not productos:
            lbl_vacio = ctk.CTkLabel(
                self.scroll_pos_catalog,
                text="No hay productos disponibles.",
                font=ctk.CTkFont(family="Arial", size=12, slant="italic"),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
            )
            lbl_vacio.pack(pady=40)
            return

        for idx, prod in enumerate(productos):
            bg_fila = self.COLOR_BG_SECUNDARIO if idx % 2 == 0 else "#212130"

            row_frame = ctk.CTkFrame(
                self.scroll_pos_catalog, fg_color=bg_fila, height=36, corner_radius=5
            )
            row_frame.pack(fill="x", pady=1, padx=2)

            for c_idx, w in enumerate(self.cat_col_weights):
                row_frame.grid_columnconfigure(c_idx, weight=w, uniform="cat_table_col")

            # Nombre
            lbl_nom = ctk.CTkLabel(
                row_frame,
                text=prod.nombre,
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="w",
            )
            lbl_nom.grid(row=0, column=0, padx=(12, 5), pady=5, sticky="w")

            # Precio
            precio = (
                prod.precio_manual
                if prod.precio_manual is not None
                else prod.precio_sugerido
            )
            lbl_prc = ctk.CTkLabel(
                row_frame,
                text=f"${precio:.2f}",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center",
            )
            lbl_prc.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

            # Disponible
            color_stk = (
                self.COLOR_INDICADOR_EXITO
                if prod.stock > 10
                else (self.COLOR_WARN if prod.stock > 0 else self.COLOR_INDICADOR_ERROR)
            )
            lbl_stk = ctk.CTkLabel(
                row_frame,
                text=str(prod.stock),
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=color_stk,
                anchor="center",
            )
            lbl_stk.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

            # Botón Agregar
            btn_add = ctk.CTkButton(
                row_frame,
                text="+ Agregar",
                fg_color=self.COLOR_BOTONES,
                hover_color=self.COLOR_BOTONES_HOVER,
                text_color="#11111b",
                width=75,
                height=22,
                font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
                command=lambda p_id=prod.id: self.agregar_al_carrito(p_id),
            )
            btn_add.grid(row=0, column=3, padx=(5, 12), pady=4, sticky="e")
            if prod.stock <= 0:
                btn_add.configure(state="disabled", fg_color=self.COLOR_BORDE)

    def agregar_al_carrito(self, producto_id: int | None) -> None:
        if producto_id is None:
            return

        prod = self.db.obtener_producto_por_id(producto_id)
        if not prod:
            return

        cant_actual = self.carrito.get(producto_id, 0)
        if prod.stock <= cant_actual:
            self.show_status_pos(
                f"No puedes agregar más '{prod.nombre}'. Stock límite alcanzado.",
                es_error=True,
            )
            return

        self.carrito[producto_id] = cant_actual + 1
        self.show_status_pos(f"'{prod.nombre}' agregado al carrito.", es_error=False)
        self.refresh_carrito_view()
        self.recalcular_totales_pos()

    def remover_del_carrito(self, producto_id: int) -> None:
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.show_status_pos("Producto removido del carrito.", es_error=False)
            self.refresh_carrito_view()
            self.recalcular_totales_pos()

    def modificar_cantidad_carrito(self, producto_id: int, cambio: int) -> None:
        if producto_id not in self.carrito:
            return

        cant = self.carrito[producto_id]
        nuevo_valor = cant + cambio

        if nuevo_valor <= 0:
            self.remover_del_carrito(producto_id)
            return

        prod = self.db.obtener_producto_por_id(producto_id)
        if not prod:
            return

        if prod.stock < nuevo_valor:
            self.show_status_pos(
                f"No hay suficiente stock disponible de '{prod.nombre}'.",
                es_error=True,
            )
            return

        self.carrito[producto_id] = nuevo_valor
        self.refresh_carrito_view()
        self.recalcular_totales_pos()

    def refresh_carrito_view(self) -> None:
        for widget in self.scroll_carrito.winfo_children():
            widget.destroy()

        if not self.carrito:
            lbl_vacio = ctk.CTkLabel(
                self.scroll_carrito,
                text="El carrito está vacío.",
                font=ctk.CTkFont(family="Arial", size=12, slant="italic"),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
            )
            lbl_vacio.pack(pady=30)
            return

        for idx, (p_id, cant) in enumerate(self.carrito.items()):
            prod = self.db.obtener_producto_por_id(p_id)
            if not prod:
                continue

            bg_fila = "#1e1e2f" if idx % 2 == 0 else "#252538"
            row_frame = ctk.CTkFrame(
                self.scroll_carrito, fg_color=bg_fila, height=36, corner_radius=5
            )
            row_frame.pack(fill="x", pady=1, padx=2)

            for c_idx, w in enumerate(self.cart_weights):
                row_frame.grid_columnconfigure(c_idx, weight=w, uniform="cart_col")

            # Nombre
            lbl_nom = ctk.CTkLabel(
                row_frame,
                text=prod.nombre,
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="w",
            )
            lbl_nom.grid(row=0, column=0, padx=10, pady=5, sticky="w")

            # Precio
            precio = (
                prod.precio_manual
                if prod.precio_manual is not None
                else prod.precio_sugerido
            )
            lbl_prc = ctk.CTkLabel(
                row_frame,
                text=f"${precio:.2f}",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center",
            )
            lbl_prc.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

            # Controles Cantidad
            frame_cant = ctk.CTkFrame(row_frame, fg_color="transparent")
            frame_cant.grid(row=0, column=2, padx=5, pady=4, sticky="center")

            btn_menos = ctk.CTkButton(
                frame_cant,
                text="-",
                width=18,
                height=18,
                fg_color=self.COLOR_BORDE,
                hover_color="#45475a",
                command=lambda pid=p_id: self.modificar_cantidad_carrito(pid, -1),
            )
            btn_menos.pack(side="left")

            lbl_cant = ctk.CTkLabel(
                frame_cant,
                text=str(cant),
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                width=24,
            )
            lbl_cant.pack(side="left", padx=3)

            btn_mas = ctk.CTkButton(
                frame_cant,
                text="+",
                width=18,
                height=18,
                fg_color=self.COLOR_BORDE,
                hover_color="#45475a",
                command=lambda pid=p_id: self.modificar_cantidad_carrito(pid, 1),
            )
            btn_mas.pack(side="left")

            # Subtotal Item
            subt = Decimal(str(cant)) * precio
            lbl_tot = ctk.CTkLabel(
                row_frame,
                text=f"${subt:.2f}",
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center",
            )
            lbl_tot.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

            # Eliminar item
            btn_del = ctk.CTkButton(
                row_frame,
                text="✕",
                fg_color="transparent",
                hover_color=self.COLOR_INDICADOR_ERROR,
                text_color=self.COLOR_TEXTO_SECUNDARIO,
                width=18,
                height=18,
                command=lambda pid=p_id: self.remover_del_carrito(pid),
            )
            btn_del.grid(row=0, column=3, padx=(0, 5), pady=4, sticky="e")

    def recalcular_totales_pos(self) -> None:
        # Sumar subtotales del carrito
        total_previo = Decimal("0.00")
        for p_id, cant in self.carrito.items():
            prod = self.db.obtener_producto_por_id(p_id)
            if prod:
                precio = (
                    prod.precio_manual
                    if prod.precio_manual is not None
                    else prod.precio_sugerido
                )
                total_previo += Decimal(str(cant)) * precio

        # Descuento
        desc_raw = self.entry_pos_descuento.get().strip()
        descuento = Decimal("0.00")
        if desc_raw:
            try:
                descuento = Decimal(desc_raw.replace(",", "."))
                if descuento < Decimal("0.00"):
                    raise InvalidOperation()
            except InvalidOperation:
                self.lbl_pos_status.configure(
                    text="Descuento inválido. Debe ser un decimal positivo.",
                    text_color=self.COLOR_INDICADOR_ERROR,
                )
                return

        if descuento > total_previo:
            descuento = total_previo

        subtotal = total_previo - descuento

        # Impuesto (16%)
        iva = (subtotal * Decimal("0.16")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total = subtotal + iva

        # Pago con
        pago_raw = self.entry_pos_pago_con.get().strip()
        pago_con = Decimal("0.00")
        cambio = Decimal("0.00")
        if pago_raw:
            try:
                pago_con = Decimal(pago_raw.replace(",", "."))
                if pago_con < Decimal("0.00"):
                    raise InvalidOperation()
            except InvalidOperation:
                self.lbl_pos_status.configure(
                    text="Monto de pago inválido.",
                    text_color=self.COLOR_INDICADOR_ERROR,
                )
                return

            if pago_con >= total:
                cambio = pago_con - total

        # Renderizar en UI
        self.lbl_pos_subtotal.configure(text=f"${total_previo:.2f}")
        self.lbl_pos_descuento_lbl.configure(text=f"-${descuento:.2f}")
        self.lbl_pos_iva.configure(text=f"${iva:.2f}")
        self.lbl_pos_total.configure(text=f"${total:.2f}")
        self.lbl_pos_cambio.configure(text=f"${cambio:.2f}")

    def procesar_cobro_pos(self) -> None:
        if not self.carrito:
            self.show_status_pos(
                "No hay productos en el carrito para cobrar.", es_error=True
            )
            return

        cajero = self.entry_cajero_id.get().strip()
        if not cajero:
            self.show_status_pos("Se requiere el ID del cajero.", es_error=True)
            return

        # Sanitización de Cajero (Zero Trust)
        if len(cajero) > 15 or not cajero.replace("-", "").isalnum():
            self.show_status_pos(
                "Cajero ID debe ser alfanumérico (máx. 15 caracteres).",
                es_error=True,
            )
            return

        # Obtener montos y validar
        try:
            desc_raw = self.entry_pos_descuento.get().strip()
            descuento = (
                Decimal(desc_raw.replace(",", ".")) if desc_raw else Decimal("0.00")
            )

            pago_raw = self.entry_pos_pago_con.get().strip()
            if not pago_raw:
                self.show_status_pos(
                    "Debe ingresar el monto de efectivo recibido.", es_error=True
                )
                return
            pago_con = Decimal(pago_raw.replace(",", "."))
        except (ValueError, InvalidOperation):
            self.show_status_pos("Montos numéricos inválidos.", es_error=True)
            return

        # Formar lista de items para Casos de Uso
        items = []
        for p_id, cant in self.carrito.items():
            items.append({"producto_id": p_id, "cantidad": cant})

        # Desencadenar caso de uso POS
        try:
            venta, err_impresora = self.pos_use_case.procesar_pago_efectivo(
                items=items,
                pago_con=pago_con,
                cajero_id=cajero,
                descuento=descuento,
            )

            self.ultima_venta_processed = venta

            if err_impresora:
                # Fallo físico de impresora capturado, no bloqueante
                self.show_status_pos(
                    f"¡VENTA {venta.id} REGISTRADA EN DB! "
                    f"Pero falló la impresora física: {err_impresora}",
                    es_error=True,
                )
                self.btn_retry_print.grid()  # Mostrar botón reintento
            else:
                self.show_status_pos(
                    f"¡Venta {venta.id} procesada con éxito! Ticket impreso.",
                    es_error=False,
                )
                self.btn_retry_print.grid_remove()

            # Vaciar carrito y actualizar vistas
            self.carrito.clear()
            self.entry_pos_pago_con.delete(0, tk.END)
            self.entry_pos_descuento.delete(0, tk.END)
            self.entry_pos_descuento.insert(0, "0.00")

            self.refresh_carrito_view()
            self.recalcular_totales_pos()
            self.refresh_pos_catalog()
            self.refresh_inventario_list()
            self.refresh_auditoria_tab()

        except ValueError as err:
            self.show_status_pos(str(err), es_error=True)
        except Exception as e:
            self.show_status_pos(
                f"Error crítico en la transacción: {str(e)}", es_error=True
            )

    def reintentar_impresion_pos(self) -> None:
        if not getattr(self, "ultima_venta_processed", None):
            return

        exito, err = self.pos_use_case.reintentar_impresion(self.ultima_venta_processed)
        if exito:
            self.show_status_pos(
                "¡Ticket reimpreso con éxito! Canal físico restaurado.",
                es_error=False,
            )
            self.btn_retry_print.grid_remove()
        else:
            self.show_status_pos(
                f"Reintento fallido: Impresora física sigue bloqueada ({err})",
                es_error=True,
            )

    def vaciar_carrito(self) -> None:
        self.carrito.clear()
        self.refresh_carrito_view()
        self.recalcular_totales_pos()
        self.show_status_pos("Carrito vaciado.", es_error=False)

    def show_status_pos(self, message: str, es_error: bool = False) -> None:
        color = self.COLOR_INDICADOR_ERROR if es_error else self.COLOR_INDICADOR_EXITO
        self.lbl_pos_status.configure(text=message, text_color=color)

    # ==========================================
    # PESTAÑA 3: AUDITORÍA DE VENTAS Y CIERRES
    # ==========================================
    def setup_tab_auditoria(self) -> None:
        """
        Crea la pestaña de auditoría (logs de operaciones críticas y visor de ventas).
        """
        self.tab_auditoria.grid_rowconfigure(1, weight=1)
        self.tab_auditoria.grid_columnconfigure(0, weight=5)  # Ventas y Detalles (50%)
        self.tab_auditoria.grid_columnconfigure(1, weight=5)  # Auditoría Log (50%)

        # Panel Superior de Cierre de Caja
        self.frame_cierre = ctk.CTkFrame(
            self.tab_auditoria, fg_color=self.COLOR_BG_SECUNDARIO, height=60
        )
        self.frame_cierre.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=(5, 10)
        )

        lbl_cajero_cierre = ctk.CTkLabel(
            self.frame_cierre,
            text="Cajero de Turno:",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        lbl_cajero_cierre.pack(side="left", padx=(15, 5), pady=12)

        self.entry_cajero_cierre = ctk.CTkEntry(
            self.frame_cierre,
            fg_color="#1e1e2e",
            border_color=self.COLOR_BORDE,
            width=130,
        )
        self.entry_cajero_cierre.pack(side="left", padx=5, pady=12)
        self.entry_cajero_cierre.insert(0, "CAJERO-01")

        self.btn_cierre_caja = ctk.CTkButton(
            self.frame_cierre,
            text="REALIZAR CIERRE DE CAJA",
            fg_color="#f9e2af",
            hover_color="#e5c890",
            text_color="#11111b",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            command=self.ejecutar_cierre_caja,
        )
        self.btn_cierre_caja.pack(side="left", padx=(15, 5), pady=12)

        # Panel Izquierdo: Ventas y detalles
        self.frame_aud_ventas = ctk.CTkFrame(self.tab_auditoria, fg_color="transparent")
        self.frame_aud_ventas.grid(row=1, column=0, sticky="nsew", padx=(5, 5), pady=5)
        self.setup_visor_ventas()

        # Panel Derecho: Registro de logs de Auditoría
        self.frame_aud_logs = ctk.CTkFrame(
            self.tab_auditoria,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=12,
        )
        self.frame_aud_logs.grid(row=1, column=1, sticky="nsew", padx=(5, 5), pady=5)
        self.setup_visor_logs_auditoria()

    def setup_visor_ventas(self) -> None:
        self.frame_aud_ventas.grid_columnconfigure(0, weight=1)
        self.frame_aud_ventas.grid_rowconfigure(1, weight=3)  # Tabla ventas
        self.frame_aud_ventas.grid_rowconfigure(3, weight=2)  # Detalles

        lbl_v_title = ctk.CTkLabel(
            self.frame_aud_ventas,
            text="VISOR DE VENTAS REGISTRADAS",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        lbl_v_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Tabla de ventas scrollable
        self.scroll_visor_ventas = ctk.CTkScrollableFrame(
            self.frame_aud_ventas,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
        )
        self.scroll_visor_ventas.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_visor_ventas.grid_columnconfigure(0, weight=1)

        # Detalles de la venta seleccionada
        self.frame_venta_detalles = ctk.CTkFrame(
            self.frame_aud_ventas,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
        )
        self.frame_venta_detalles.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        self.frame_venta_detalles.grid_columnconfigure(0, weight=1)
        self.frame_venta_detalles.grid_rowconfigure(1, weight=1)

        self.lbl_det_title = ctk.CTkLabel(
            self.frame_venta_detalles,
            text="Detalles de Venta Seleccionada",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_det_title.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.scroll_detalles_venta = ctk.CTkScrollableFrame(
            self.frame_venta_detalles, fg_color="#1e1e2f"
        )
        self.scroll_detalles_venta.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.scroll_detalles_venta.grid_columnconfigure(0, weight=1)

        # Botones de Acción de Venta
        self.frame_det_acciones = ctk.CTkFrame(
            self.frame_venta_detalles, fg_color="transparent"
        )
        self.frame_det_acciones.grid(row=2, column=0, sticky="ew", padx=15, pady=10)

        self.btn_anular_venta = ctk.CTkButton(
            self.frame_det_acciones,
            text="ANULAR VENTA SELECCIONADA",
            fg_color=self.COLOR_INDICADOR_ERROR,
            hover_color="#eba0ac",
            text_color="#11111b",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            command=self.confirmar_anulacion_venta,
        )
        self.btn_anular_venta.pack(side="left")
        self.btn_anular_venta.configure(state="disabled")

    def setup_visor_logs_auditoria(self) -> None:
        self.frame_aud_logs.grid_columnconfigure(0, weight=1)
        self.frame_aud_logs.grid_rowconfigure(1, weight=1)

        lbl_l_title = ctk.CTkLabel(
            self.frame_aud_logs,
            text="REGISTRO DE AUDITORÍA (AUDIT TRAIL)",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        lbl_l_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        # Scroll de logs
        self.scroll_auditoria_logs = ctk.CTkScrollableFrame(
            self.frame_aud_logs, fg_color="#1e1e2f"
        )
        self.scroll_auditoria_logs.grid(
            row=1, column=0, sticky="nsew", padx=15, pady=(0, 15)
        )
        self.scroll_auditoria_logs.grid_columnconfigure(0, weight=1)

    def refresh_auditoria_tab(self) -> None:
        # 1. Recargar visor de ventas
        for widget in self.scroll_visor_ventas.winfo_children():
            widget.destroy()

        try:
            ventas = self.db.obtener_ventas()
        except Exception:
            return

        if not ventas:
            lbl = ctk.CTkLabel(
                self.scroll_visor_ventas,
                text="No hay ventas registradas aún.",
                font=ctk.CTkFont(family="Arial", size=12, slant="italic"),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
            )
            lbl.pack(pady=30)
        else:
            for idx, v in enumerate(ventas):
                bg_fila = self.COLOR_BG_SECUNDARIO if idx % 2 == 0 else "#212130"
                row_f = ctk.CTkFrame(
                    self.scroll_visor_ventas,
                    fg_color=bg_fila,
                    height=36,
                    corner_radius=5,
                )
                row_f.pack(fill="x", pady=2, padx=2)

                # Grid column split
                row_f.grid_columnconfigure(0, weight=1)  # ID
                row_f.grid_columnconfigure(1, weight=3)  # Fecha
                row_f.grid_columnconfigure(2, weight=2)  # Total
                row_f.grid_columnconfigure(3, weight=2)  # Cajero
                row_f.grid_columnconfigure(4, weight=2)  # Estado

                # Clickable binding to load details
                v_id = v["id"]
                row_f.bind(
                    "<Button-1>", lambda e, vid=v_id: self.cargar_detalles_venta(vid)
                )

                # ID
                lbl_id = ctk.CTkLabel(
                    row_f,
                    text=f"ID: {v['id']}",
                    font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                    text_color=self.COLOR_TEXTO_PRINCIPAL,
                    anchor="w",
                )
                lbl_id.grid(row=0, column=0, padx=8, pady=5, sticky="w")
                lbl_id.bind(
                    "<Button-1>", lambda e, vid=v_id: self.cargar_detalles_venta(vid)
                )

                # Fecha
                fecha_f = v["fecha_hora"][:19].replace("T", " ")
                lbl_fec = ctk.CTkLabel(
                    row_f,
                    text=fecha_f,
                    font=ctk.CTkFont(family="Arial", size=10),
                    text_color=self.COLOR_TEXTO_SECUNDARIO,
                    anchor="center",
                )
                lbl_fec.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
                lbl_fec.bind(
                    "<Button-1>", lambda e, vid=v_id: self.cargar_detalles_venta(vid)
                )

                # Total
                lbl_tot = ctk.CTkLabel(
                    row_f,
                    text=f"${v['total']:.2f}",
                    font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                    text_color=self.COLOR_BOTONES,
                    anchor="center",
                )
                lbl_tot.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
                lbl_tot.bind(
                    "<Button-1>", lambda e, vid=v_id: self.cargar_detalles_venta(vid)
                )

                # Cajero
                lbl_caj = ctk.CTkLabel(
                    row_f,
                    text=v["cajero_id"],
                    font=ctk.CTkFont(family="Arial", size=10),
                    text_color=self.COLOR_TEXTO_SECUNDARIO,
                    anchor="center",
                )
                lbl_caj.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
                lbl_caj.bind(
                    "<Button-1>", lambda e, vid=v_id: self.cargar_detalles_venta(vid)
                )

                # Estado
                color_estado = (
                    self.COLOR_INDICADOR_EXITO
                    if v["estado"] == "COMPLETADA"
                    else (
                        self.COLOR_INDICADOR_ERROR
                        if v["estado"] == "ANULADA"
                        else self.COLOR_WARN
                    )
                )
                lbl_est = ctk.CTkLabel(
                    row_f,
                    text=v["estado"],
                    font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
                    text_color=color_estado,
                    anchor="center",
                )
                lbl_est.grid(row=0, column=4, padx=8, pady=5, sticky="ew")
                lbl_est.bind(
                    "<Button-1>", lambda e, vid=v_id: self.cargar_detalles_venta(vid)
                )

        # 2. Recargar visor de logs de auditoria (Audit Trail)
        for widget in self.scroll_auditoria_logs.winfo_children():
            widget.destroy()

        try:
            logs = self.db.obtener_logs_auditoria()
        except Exception:
            return

        if not logs:
            lbl = ctk.CTkLabel(
                self.scroll_auditoria_logs,
                text="No hay registros en la auditoría.",
                font=ctk.CTkFont(family="Arial", size=12, slant="italic"),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
            )
            lbl.pack(pady=30)
        else:
            for log in logs:
                log_box = ctk.CTkFrame(
                    self.scroll_auditoria_logs,
                    fg_color="#181825",
                    border_color=self.COLOR_BORDE,
                    border_width=1,
                    corner_radius=6,
                )
                log_box.pack(fill="x", pady=3, padx=2)

                # Cabecera del log
                color_op = self.COLOR_BOTONES
                if log["operacion"] == "ANULACION":
                    color_op = self.COLOR_INDICADOR_ERROR
                elif log["operacion"] == "CIERRE_CAJA":
                    color_op = self.COLOR_WARN

                fecha_l = log["fecha_hora"][:19].replace("T", " ")

                lbl_head = ctk.CTkLabel(
                    log_box,
                    text=f"[{fecha_l}] {log['operacion']} - Cajero: {log['cajero_id']}",
                    font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                    text_color=color_op,
                    anchor="w",
                )
                lbl_head.pack(fill="x", padx=10, pady=(5, 2))

                # Anterior/Nuevo
                if log["estado_anterior"] or log["estado_nuevo"]:
                    texto_estados = (
                        f"Ant: {log['estado_anterior']} | Nvo: {log['estado_nuevo']}"
                    )
                    lbl_states = ctk.CTkLabel(
                        log_box,
                        text=texto_estados,
                        font=ctk.CTkFont(family="Arial", size=10, slant="italic"),
                        text_color=self.COLOR_TEXTO_SECUNDARIO,
                        anchor="w",
                    )
                    lbl_states.pack(fill="x", padx=10, pady=1)

                # Detalles
                lbl_det = ctk.CTkLabel(
                    log_box,
                    text=log["detalles"],
                    font=ctk.CTkFont(family="Arial", size=11),
                    text_color=self.COLOR_TEXTO_PRINCIPAL,
                    anchor="w",
                    wraplength=480,
                    justify="left",
                )
                lbl_det.pack(fill="x", padx=10, pady=(1, 5))

    def cargar_detalles_venta(self, venta_id: int) -> None:
        self.venta_seleccionada_id = venta_id

        # Limpiar
        for widget in self.scroll_detalles_venta.winfo_children():
            widget.destroy()

        # Obtener venta y detalles de forma segura a través del repositorio
        # (la capa de presentación jamás accede directamente a la conexión SQLite).
        rows = self.db.obtener_detalles_venta(venta_id)

        if not rows:
            return

        self.lbl_det_title.configure(
            text=f"Detalles de Venta ID {venta_id} - Estado: {rows[0]['estado']}"
        )

        # Botón anulación activo si no está ya anulada
        if rows[0]["estado"] == "ANULADA":
            self.btn_anular_venta.configure(state="disabled")
        else:
            self.btn_anular_venta.configure(state="normal")

        # Detalle cabecera columnas
        headers_frame = ctk.CTkFrame(self.scroll_detalles_venta, fg_color="#181825")
        headers_frame.pack(fill="x", pady=2)

        lbl_header_n = ctk.CTkLabel(
            headers_frame,
            text="Producto",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        lbl_header_n.pack(side="left", padx=10)

        lbl_header_t = ctk.CTkLabel(
            headers_frame,
            text="Total",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
            anchor="e",
        )
        lbl_header_t.pack(side="right", padx=10)

        lbl_header_c = ctk.CTkLabel(
            headers_frame,
            text="Cant x Precio",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
            anchor="center",
        )
        lbl_header_c.pack(side="right", padx=20)

        for r in rows:
            item_frame = ctk.CTkFrame(
                self.scroll_detalles_venta, fg_color="transparent"
            )
            item_frame.pack(fill="x", pady=2)

            lbl_name = ctk.CTkLabel(
                item_frame,
                text=r["nombre"],
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
            )
            lbl_name.pack(side="left", padx=10)

            lbl_subt = ctk.CTkLabel(
                item_frame,
                text=f"${r['subtotal']:.2f}",
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
            )
            lbl_subt.pack(side="right", padx=10)

            lbl_qty_prc = ctk.CTkLabel(
                item_frame,
                text=f"{r['cantidad']} x ${r['precio_unitario']:.2f}",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
            )
            lbl_qty_prc.pack(side="right", padx=20)

    def confirmar_anulacion_venta(self) -> None:
        if self.venta_seleccionada_id is None:
            return

        cajero = self.entry_cajero_cierre.get().strip()
        if not cajero:
            cajero = "SISTEMA"

        dialog = CustomConfirmDialog(
            self,
            title="Confirmar Anulación",
            message=(
                f"¿Está seguro de que desea ANULAR la venta "
                f"ID {self.venta_seleccionada_id}?\n"
                "Se restaurará el stock y se registrará un log de auditoría."
            ),
        )

        if dialog.result:
            try:
                self.pos_use_case.anular_ticket(self.venta_seleccionada_id, cajero)
                # Recargar
                self.refresh_auditoria_tab()
                self.refresh_pos_catalog()
                self.refresh_inventario_list()

                # Limpiar visor detalles
                for widget in self.scroll_detalles_venta.winfo_children():
                    widget.destroy()
                self.lbl_det_title.configure(text="Detalles de Venta Seleccionada")
                self.btn_anular_venta.configure(state="disabled")

                # Mensaje de exito popup local
                messagebox.showinfo(
                    "Anulación Exitosa",
                    f"Venta {self.venta_seleccionada_id} anulada con éxito.",
                )

            except Exception as e:
                messagebox.showerror("Error al Anular", str(e))

    def ejecutar_cierre_caja(self) -> None:
        cajero = self.entry_cajero_cierre.get().strip()
        if not cajero:
            messagebox.showwarning(
                "ID requerido",
                "Ingrese el ID del cajero para realizar el cierre de caja.",
            )
            return

        dialog = CustomConfirmDialog(
            self,
            title="Cierre de Caja",
            message=(
                f"¿Desea cerrar la caja de la sesión activa para '{cajero}'?\n"
                "Se calculará el balance del turno y se registrará en auditoría."
            ),
        )

        if dialog.result:
            try:
                resumen = self.pos_use_case.realizar_cierre_de_caja(cajero)

                self.refresh_auditoria_tab()

                # Mostrar popup resumen de cierre
                mensaje_cierre = (
                    f"=== CIERRE DE CAJA EXITOSO ===\n"
                    f"Cajero: {cajero}\n"
                    f"Total de Ventas: {resumen['cantidad_ventas']}\n"
                    f"Monto Total Recaudado: ${resumen['total_ventas']:.2f}\n"
                    f"Descuentos Especiales Aplicados: "
                    f"${resumen['total_descuentos']:.2f}\n"
                    f"=============================="
                )

                messagebox.showinfo("Resumen Cierre Caja", mensaje_cierre)

            except Exception as e:
                messagebox.showerror("Error de Cierre", str(e))
