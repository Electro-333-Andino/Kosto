"""
presentation/gui.py

Este módulo implementa la interfaz gráfica de usuario (GUI) utilizando CustomTkinter.
Sigue estrictamente la paleta de colores de Catppuccin Mocha y una arquitectura limpia.
No contiene lógica de negocios ni de acceso a datos directa, sino que delega en el Dominio y el DatabaseManager.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from domain.models import Producto
from infrastructure.database import DatabaseManager


class KostoApp(ctk.CTk):
    """
    Ventana principal del sistema de control de inventario Kosto.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db

        # Guardar estado de edición
        self.producto_seleccionado_id: Optional[int] = None

        # Configuración básica de la ventana
        self.title("KOSTO - Control de Inventario y Márgenes")
        self.geometry("1150x680")
        self.minsize(1050, 600)

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

        # Aplicar fondo principal
        self.configure(fg_color=self.COLOR_BG_PRINCIPAL)

        # Crear estructura de la interfaz (2 secciones principales)
        self.setup_layout()

        # Cargar lista de productos inicial
        self.refresh_list()

    def setup_layout(self) -> None:
        """
        Divide la interfaz en dos paneles principales: izquierdo (formulario) y derecho (tabla).
        """
        # Configurar grid principal (1 fila, 2 columnas)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)  # Formulario (30%)
        self.grid_columnconfigure(1, weight=7)  # Tabla (70%)

        # ==========================================
        # PANEL IZQUIERDO: FORMULARIO DE INGRESO
        # ==========================================
        self.frame_formulario = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=12,
        )
        self.frame_formulario.grid(
            row=0, column=0, sticky="nsew", padx=(15, 7), pady=15
        )
        self.setup_formulario()

        # ==========================================
        # PANEL DERECHO: VISUALIZACIÓN / BÚSQUEDA
        # ==========================================
        self.frame_tabla = ctk.CTkFrame(self, fg_color=self.COLOR_BG_PRINCIPAL)
        self.frame_tabla.grid(row=0, column=1, sticky="nsew", padx=(7, 15), pady=15)
        self.setup_tabla()

    def setup_formulario(self) -> None:
        """
        Crea los campos del formulario de ingreso y edición en el panel izquierdo.
        """
        self.frame_formulario.grid_columnconfigure(0, weight=1)

        # Título del Formulario
        self.lbl_form_title = ctk.CTkLabel(
            self.frame_formulario,
            text="REGISTRAR PRODUCTO",
            font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_form_title.grid(row=0, column=0, padx=20, pady=(25, 20), sticky="w")

        # Campo: Nombre del Producto
        self.lbl_nombre = ctk.CTkLabel(
            self.frame_formulario,
            text="Nombre del Producto:",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_nombre.grid(row=1, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_nombre = ctk.CTkEntry(
            self.frame_formulario,
            placeholder_text="Ej. Aceite de Oliva",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=35,
        )
        self.entry_nombre.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.entry_nombre.bind("<KeyRelease>", lambda e: self.recalcular_form())

        # Campo: Costo Total del Paquete
        self.lbl_costo_total = ctk.CTkLabel(
            self.frame_formulario,
            text="Costo Total del Paquete ($):",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_costo_total.grid(row=3, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_costo_total = ctk.CTkEntry(
            self.frame_formulario,
            placeholder_text="Ej. 3.67",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=35,
        )
        self.entry_costo_total.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.entry_costo_total.bind("<KeyRelease>", lambda e: self.recalcular_form())

        # Campo: Unidades por Paquete
        self.lbl_unidades = ctk.CTkLabel(
            self.frame_formulario,
            text="Unidades por Paquete:",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_unidades.grid(row=5, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_unidades = ctk.CTkEntry(
            self.frame_formulario,
            placeholder_text="Ej. 12",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=35,
        )
        self.entry_unidades.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.entry_unidades.bind("<KeyRelease>", lambda e: self.recalcular_form())

        # Separador / Sección de Cálculos en tiempo real
        self.frame_calculos = ctk.CTkFrame(
            self.frame_formulario,
            fg_color=self.COLOR_BG_PRINCIPAL,
            corner_radius=8,
            border_color=self.COLOR_BORDE,
            border_width=1,
        )
        self.frame_calculos.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.frame_calculos.grid_columnconfigure((0, 1), weight=1)

        # Costo unitario real (Label)
        self.lbl_costo_unitario = ctk.CTkLabel(
            self.frame_calculos,
            text="Costo Unit. Real:",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_costo_unitario.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")

        self.lbl_costo_unitario_val = ctk.CTkLabel(
            self.frame_calculos,
            text="$0.0000",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_costo_unitario_val.grid(
            row=0, column=1, padx=12, pady=(10, 2), sticky="e"
        )

        # Precio de venta sugerido (Label)
        self.lbl_precio_sugerido = ctk.CTkLabel(
            self.frame_calculos,
            text="Precio Sugerido:",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_precio_sugerido.grid(row=1, column=0, padx=12, pady=2, sticky="w")

        self.lbl_precio_sugerido_val = ctk.CTkLabel(
            self.frame_calculos,
            text="$0.00",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_precio_sugerido_val.grid(row=1, column=1, padx=12, pady=2, sticky="e")

        # Campo: Precio de Venta Manual
        self.lbl_precio_manual = ctk.CTkLabel(
            self.frame_formulario,
            text="Precio de Venta Manual ($):",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_SECUNDARIO,
        )
        self.lbl_precio_manual.grid(row=8, column=0, padx=20, pady=(5, 2), sticky="w")

        self.entry_precio_manual = ctk.CTkEntry(
            self.frame_formulario,
            placeholder_text="Dejar vacío para usar el sugerido",
            fg_color=self.COLOR_BG_PRINCIPAL,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=35,
        )
        self.entry_precio_manual.grid(
            row=9, column=0, padx=20, pady=(0, 15), sticky="ew"
        )
        self.entry_precio_manual.bind(
            "<KeyRelease>", lambda e: self.recalcular_form(manual_override=True)
        )

        # Ganancia neta (Label destacada)
        self.frame_ganancia = ctk.CTkFrame(
            self.frame_formulario,
            fg_color=self.COLOR_BG_PRINCIPAL,
            corner_radius=8,
            border_color=self.COLOR_BORDE,
            border_width=1,
        )
        self.frame_ganancia.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.frame_ganancia.grid_columnconfigure((0, 1), weight=1)

        self.lbl_ganancia = ctk.CTkLabel(
            self.frame_ganancia,
            text="Ganancia por Unidad:",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color=self.COLOR_TEXTO_PRINCIPAL,
        )
        self.lbl_ganancia.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.lbl_ganancia_val = ctk.CTkLabel(
            self.frame_ganancia,
            text="$0.0000",
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            text_color=self.COLOR_INDICADOR_EXITO,
        )
        self.lbl_ganancia_val.grid(row=0, column=1, padx=12, pady=10, sticky="e")

        # Estado/Log de errores o éxitos
        self.lbl_status = ctk.CTkLabel(
            self.frame_formulario,
            text="",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color=self.COLOR_INDICADOR_EXITO,
            wraplength=280,
        )
        self.lbl_status.grid(row=11, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Botones de Acción
        self.frame_botones_form = ctk.CTkFrame(
            self.frame_formulario, fg_color="transparent"
        )
        self.frame_botones_form.grid(
            row=12, column=0, padx=20, pady=(0, 20), sticky="ew"
        )
        self.frame_botones_form.grid_columnconfigure((0, 1), weight=1)

        self.btn_guardar = ctk.CTkButton(
            self.frame_botones_form,
            text="Guardar",
            fg_color=self.COLOR_BOTONES,
            hover_color=self.COLOR_BOTONES_HOVER,
            text_color="#11111b",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            height=38,
            command=self.guardar_producto,
        )
        self.btn_guardar.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.btn_limpiar = ctk.CTkButton(
            self.frame_botones_form,
            text="Limpiar",
            fg_color=self.COLOR_BORDE,
            hover_color="#45475a",
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            height=38,
            command=self.limpiar_formulario,
        )
        self.btn_limpiar.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def setup_tabla(self) -> None:
        """
        Crea el buscador y la estructura de la tabla de visualización en el panel derecho.
        """
        self.frame_tabla.grid_columnconfigure(0, weight=1)
        self.frame_tabla.grid_rowconfigure(2, weight=1)

        # Buscador superior
        self.frame_buscador = ctk.CTkFrame(self.frame_tabla, fg_color="transparent")
        self.frame_buscador.grid(row=0, column=0, sticky="ew", pady=(0, 15))
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
            placeholder_text="Escribe el nombre de un producto para filtrar en tiempo real...",
            fg_color=self.COLOR_BG_SECUNDARIO,
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            border_color=self.COLOR_BORDE,
            height=35,
        )
        self.entry_buscar.grid(row=0, column=1, sticky="ew")
        self.entry_buscar.bind("<KeyRelease>", lambda e: self.refresh_list())

        self.btn_limpiar_buscar = ctk.CTkButton(
            self.frame_buscador,
            text="Limpiar Filtro",
            fg_color=self.COLOR_BORDE,
            hover_color="#45475a",
            text_color=self.COLOR_TEXTO_PRINCIPAL,
            width=100,
            height=35,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            command=self.limpiar_busqueda,
        )
        self.btn_limpiar_buscar.grid(row=0, column=2, padx=(10, 0))

        # Encabezado de la tabla (Header row)
        self.frame_headers = ctk.CTkFrame(
            self.frame_tabla,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
            height=40,
        )
        self.frame_headers.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        # Grid para las columnas de cabecera
        # Configurar anchos proporcionales idénticos a los de las filas
        self.column_weights = [
            4,
            2,
            1,
            2,
            2,
            2,
            2,
            3,
        ]  # Ajustado: Nombre tiene 4, Unidades 1, Acciones 3, etc.
        for idx, w in enumerate(self.column_weights):
            self.frame_headers.grid_columnconfigure(idx, weight=w, uniform="table_col")

        headers = [
            "Nombre",
            "Costo Paq.",
            "Unids.",
            "Costo Unit.",
            "P. Sugerido",
            "P. Venta",
            "Ganancia Unit.",
            "Acciones",
        ]

        for idx, text in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.frame_headers,
                text=text,
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center" if idx > 0 else "w",
            )
            padx_lbl = (12, 5) if idx == 0 else 5
            lbl.grid(
                row=0,
                column=idx,
                padx=padx_lbl,
                pady=10,
                sticky="ew" if idx > 0 else "w",
            )

        # Contenedor con scroll para los datos de los productos
        self.scroll_table = ctk.CTkScrollableFrame(
            self.frame_tabla,
            fg_color=self.COLOR_BG_SECUNDARIO,
            border_color=self.COLOR_BORDE,
            border_width=1,
            corner_radius=8,
        )
        self.scroll_table.grid(row=2, column=0, sticky="nsew")
        self.scroll_table.grid_columnconfigure(0, weight=1)

    def recalcular_form(self, manual_override: bool = False) -> None:
        """
        Realiza cálculos en tiempo real en memoria usando el modelo de dominio.
        Actualiza los indicadores sin disparar molestas alertas mientras el usuario escribe.
        """
        nombre = self.entry_nombre.get().strip()
        costo_total_raw = self.entry_costo_total.get().strip()
        unidades_raw = self.entry_unidades.get().strip()
        precio_manual_raw = self.entry_precio_manual.get().strip()

        # Ocultar temporalmente logs de estado al recalcular activamente
        self.lbl_status.configure(text="")

        if not nombre or not costo_total_raw or not unidades_raw:
            # Estado incompleto: Limpiar cálculos derivados
            self.lbl_costo_unitario_val.configure(text="$0.0000")
            self.lbl_precio_sugerido_val.configure(text="$0.00")
            self.lbl_ganancia_val.configure(
                text="$0.0000", text_color=self.COLOR_INDICADOR_EXITO
            )
            return

        try:
            # Limpieza básica para permitir comas como punto decimal
            costo_total = float(costo_total_raw.replace(",", "."))
            unidades = int(unidades_raw)

            if costo_total <= 0 or unidades <= 0:
                raise ValueError()
        except ValueError:
            # Inputs inválidos pero el usuario podría estar a mitad de escribir
            self.lbl_costo_unitario_val.configure(
                text="Invalido", text_color=self.COLOR_INDICADOR_ERROR
            )
            self.lbl_precio_sugerido_val.configure(
                text="Invalido", text_color=self.COLOR_INDICADOR_ERROR
            )
            self.lbl_ganancia_val.configure(
                text="Invalido", text_color=self.COLOR_INDICADOR_ERROR
            )
            return

        # Restablecer colores originales
        self.lbl_costo_unitario_val.configure(text_color=self.COLOR_TEXTO_PRINCIPAL)
        self.lbl_precio_sugerido_val.configure(text_color=self.COLOR_TEXTO_PRINCIPAL)

        try:
            # Instanciar modelo de dominio en memoria
            # Si el precio manual no ha sido tocado por el usuario o está vacío, dejamos que calcule el sugerido
            p_manual = None
            if precio_manual_raw:
                try:
                    p_manual = float(precio_manual_raw.replace(",", "."))
                except ValueError:
                    pass

            prod_temp = Producto(
                nombre=nombre,
                costo_total=costo_total,
                unidades_por_paquete=unidades,
                precio_manual=p_manual,
            )

            # Si el cálculo actualiza el precio sugerido y el usuario no especificó un precio manual,
            # o si NO estamos haciendo override manual del precio, pre-llenar de forma amigable
            if not manual_override and not precio_manual_raw:
                # No reescribir si ya hay un valor ingresado a menos que sea igual al anterior sugerido
                self.entry_precio_manual.delete(0, tk.END)
                self.entry_precio_manual.insert(0, f"{prod_temp.precio_sugerido:.2f}")
                prod_temp.update_precio_manual(prod_temp.precio_sugerido)

            # Mostrar cálculos actualizados en la GUI
            self.lbl_costo_unitario_val.configure(
                text=f"${prod_temp.costo_unitario_real:.4f}"
            )
            self.lbl_precio_sugerido_val.configure(
                text=f"${prod_temp.precio_sugerido:.2f}"
            )
            self.lbl_ganancia_val.configure(text=f"${prod_temp.ganancia_neta:.4f}")

            # Dar color al indicador de ganancia
            if prod_temp.ganancia_neta >= 0:
                self.lbl_ganancia_val.configure(text_color=self.COLOR_INDICADOR_EXITO)
            else:
                self.lbl_ganancia_val.configure(text_color=self.COLOR_INDICADOR_ERROR)

        except ValueError as err:
            # Manejar errores de dominio de forma elegante
            self.lbl_ganancia_val.configure(
                text="Error Calc.", text_color=self.COLOR_INDICADOR_ERROR
            )

    def guardar_producto(self) -> None:
        """
        Valida rigurosamente los campos del formulario y persiste el producto (nuevo o actualizado).
        """
        nombre = self.entry_nombre.get().strip()
        costo_total_raw = self.entry_costo_total.get().strip()
        unidades_raw = self.entry_unidades.get().strip()
        precio_manual_raw = self.entry_precio_manual.get().strip()

        # Validaciones de la UI antes de instanciar
        if not nombre:
            self.show_status("El nombre del producto es requerido.", es_error=True)
            return

        try:
            costo_total = float(costo_total_raw.replace(",", "."))
        except ValueError:
            self.show_status(
                "El costo del paquete debe ser un número decimal.", es_error=True
            )
            return

        try:
            unidades = int(unidades_raw)
        except ValueError:
            self.show_status(
                "Las unidades por paquete deben ser un entero.", es_error=True
            )
            return

        precio_manual = None
        if precio_manual_raw:
            try:
                precio_manual = float(precio_manual_raw.replace(",", "."))
            except ValueError:
                self.show_status(
                    "El precio de venta manual debe ser un número válido.",
                    es_error=True,
                )
                return

        try:
            # Crear entidad de dominio para asegurar consistencia
            producto = Producto(
                nombre=nombre,
                costo_total=costo_total,
                unidades_por_paquete=unidades,
                precio_manual=precio_manual,
            )
        except ValueError as err:
            self.show_status(str(err), es_error=True)
            return

        # Decidir si es inserción o actualización
        if self.producto_seleccionado_id is None:
            # Registrar nuevo producto
            try:
                self.db.insertar_producto(producto)
                self.show_status(
                    f"¡'{producto.nombre}' registrado con éxito!", es_error=False
                )
                self.limpiar_formulario()
            except Exception as e:
                self.show_status(f"Error al guardar: {str(e)}", es_error=True)
        else:
            # Guardar cambios del producto existente
            try:
                producto.id = self.producto_seleccionado_id
                self.db.actualizar_producto(producto)
                self.show_status(
                    f"¡'{producto.nombre}' actualizado con éxito!", es_error=False
                )
                self.limpiar_formulario()
            except Exception as e:
                self.show_status(f"Error al actualizar: {str(e)}", es_error=True)

        # Recargar lista de visualización
        self.refresh_list()

    def refresh_list(self) -> None:
        """
        Actualiza los registros que se muestran en el scroll_table,
        aplicando filtros de búsqueda en tiempo real si existen de manera segura.
        """
        # Limpiar widgets actuales en la tabla scrollable
        for widget in self.scroll_table.winfo_children():
            widget.destroy()

        busqueda = self.entry_buscar.get().strip()

        try:
            # Obtener datos de la BD de forma parametrizada y segura
            productos = self.db.obtener_productos(busqueda=busqueda)
        except Exception as e:
            # En caso de error, mostrarlo y retornar
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
                text="No se encontraron productos registrados.",
                font=ctk.CTkFont(family="Arial", size=13, slant="italic"),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
            )
            lbl_vacio.pack(pady=40)
            return

        # Agregar los productos a la vista como filas perfectamente alineadas
        for idx, prod in enumerate(productos):
            # Frame contenedor para la fila
            # Color alternado sutil para mejorar la legibilidad visual de la tabla
            bg_fila = self.COLOR_BG_SECUNDARIO if idx % 2 == 0 else "#212130"

            row_frame = ctk.CTkFrame(
                self.scroll_table, fg_color=bg_fila, height=45, corner_radius=6
            )
            row_frame.pack(fill="x", pady=2, padx=2)

            # Configurar misma distribución de pesos que la cabecera
            for c_idx, w in enumerate(self.column_weights):
                row_frame.grid_columnconfigure(c_idx, weight=w, uniform="table_col")

            # Columna 0: Nombre
            lbl_nom = ctk.CTkLabel(
                row_frame,
                text=prod.nombre,
                font=ctk.CTkFont(family="Arial", size=12),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="w",
            )
            lbl_nom.grid(row=0, column=0, padx=(12, 5), pady=8, sticky="w")

            # Columna 1: Costo total paquete
            lbl_costo_p = ctk.CTkLabel(
                row_frame,
                text=f"${prod.costo_total:.2f}",
                font=ctk.CTkFont(family="Arial", size=12),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center",
            )
            lbl_costo_p.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

            # Columna 2: Unidades
            lbl_unid = ctk.CTkLabel(
                row_frame,
                text=str(prod.unidades_por_paquete),
                font=ctk.CTkFont(family="Arial", size=12),
                text_color=self.COLOR_TEXTO_PRINCIPAL,
                anchor="center",
            )
            lbl_unid.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

            # Columna 3: Costo Unitario Real (4 decimales)
            lbl_costo_u = ctk.CTkLabel(
                row_frame,
                text=f"${prod.costo_unitario_real:.4f}",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
                anchor="center",
            )
            lbl_costo_u.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

            # Columna 4: Precio sugerido (2 decimales)
            lbl_sug = ctk.CTkLabel(
                row_frame,
                text=f"${prod.precio_sugerido:.2f}",
                font=ctk.CTkFont(family="Arial", size=12),
                text_color=self.COLOR_TEXTO_SECUNDARIO,
                anchor="center",
            )
            lbl_sug.grid(row=0, column=4, padx=5, pady=8, sticky="ew")

            # Columna 5: Precio venta final / manual (2 decimales)
            lbl_man = ctk.CTkLabel(
                row_frame,
                text=f"${prod.precio_manual:.2f}",
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                text_color=self.COLOR_BOTONES,
                anchor="center",
            )
            lbl_man.grid(row=0, column=5, padx=5, pady=8, sticky="ew")

            # Columna 6: Ganancia neta (4 decimales)
            color_ganancia = (
                self.COLOR_INDICADOR_EXITO
                if prod.ganancia_neta >= 0
                else self.COLOR_INDICADOR_ERROR
            )
            lbl_gan = ctk.CTkLabel(
                row_frame,
                text=f"${prod.ganancia_neta:.4f}",
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                text_color=color_ganancia,
                anchor="center",
            )
            lbl_gan.grid(row=0, column=6, padx=5, pady=8, sticky="ew")

            # Columna 7: Acciones (Botones Editar / Eliminar)
            frame_acciones = ctk.CTkFrame(row_frame, fg_color="transparent")
            frame_acciones.grid(row=0, column=7, padx=(5, 12), pady=4, sticky="e")

            btn_edit = ctk.CTkButton(
                frame_acciones,
                text="✎",
                fg_color=self.COLOR_BOTONES,
                hover_color=self.COLOR_BOTONES_HOVER,
                text_color="#11111b",
                width=30,
                height=26,
                font=ctk.CTkFont(family="Arial", size=12),
                command=lambda p=prod: self.cargar_producto_edicion(p),
            )
            btn_edit.pack(side="left", padx=2)

            btn_delete = ctk.CTkButton(
                frame_acciones,
                text="🗑",
                fg_color=self.COLOR_INDICADOR_ERROR,
                hover_color="#eba0ac",
                text_color="#11111b",
                width=30,
                height=26,
                font=ctk.CTkFont(family="Arial", size=12),
                command=lambda p=prod: self.confirmar_eliminar(p),
            )
            btn_delete.pack(side="left", padx=2)

    def cargar_producto_edicion(self, producto: Producto) -> None:
        """
        Carga los datos de un producto seleccionado en el formulario y cambia el modo a 'Edición'.
        """
        self.producto_seleccionado_id = producto.id

        # Limpiar form antes de insertar
        self.entry_nombre.delete(0, tk.END)
        self.entry_nombre.insert(0, producto.nombre)

        self.entry_costo_total.delete(0, tk.END)
        self.entry_costo_total.insert(0, str(producto.costo_total))

        self.entry_unidades.delete(0, tk.END)
        self.entry_unidades.insert(0, str(producto.unidades_por_paquete))

        self.entry_precio_manual.delete(0, tk.END)
        self.entry_precio_manual.insert(0, str(producto.precio_manual))

        # Cambiar apariencia del título del formulario y botones
        self.lbl_form_title.configure(
            text=f"EDITAR PRODUCTO (ID: {producto.id})", text_color=self.COLOR_BOTONES
        )
        self.btn_guardar.configure(
            text="Guardar Cambios",
            fg_color=self.COLOR_INDICADOR_EXITO,
            hover_color="#c2f2bd",
        )

        # Forzar recalcular para refrescar los labels calculados en tiempo real
        self.recalcular_form(manual_override=True)
        self.show_status(
            "Producto cargado para edición. Modifica los campos y haz clic en 'Guardar Cambios'.",
            es_error=False,
        )

    def confirmar_eliminar(self, producto: Producto) -> None:
        """
        Muestra un cuadro de diálogo para confirmar la eliminación de un producto de forma segura.
        """
        if producto.id is None:
            return

        respuesta = messagebox.askyesno(
            title="Confirmar eliminación",
            message=f"¿Está seguro de que desea eliminar el producto '{producto.nombre}'?\nEsta acción no se puede deshacer.",
            parent=self,
        )

        if respuesta:
            try:
                self.db.eliminar_producto(producto.id)
                self.show_status(
                    f"Producto '{producto.nombre}' eliminado con éxito.", es_error=False
                )

                # Si el producto eliminado era el que se estaba editando, limpiar el form
                if self.producto_seleccionado_id == producto.id:
                    self.limpiar_formulario()

                self.refresh_list()
            except Exception as e:
                self.show_status(f"Error al eliminar: {str(e)}", es_error=True)

    def limpiar_formulario(self) -> None:
        """
        Limpia todos los campos del formulario y restablece el estado a modo 'Registro'.
        """
        self.producto_seleccionado_id = None

        self.entry_nombre.delete(0, tk.END)
        self.entry_costo_total.delete(0, tk.END)
        self.entry_unidades.delete(0, tk.END)
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

        # Restablecer estética del formulario a modo de Registro
        self.lbl_form_title.configure(
            text="REGISTRAR PRODUCTO", text_color=self.COLOR_TEXTO_PRINCIPAL
        )
        self.btn_guardar.configure(
            text="Guardar",
            fg_color=self.COLOR_BOTONES,
            hover_color=self.COLOR_BOTONES_HOVER,
        )

    def limpiar_busqueda(self) -> None:
        """
        Limpia la barra de búsqueda y refresca la lista completa de productos.
        """
        self.entry_buscar.delete(0, tk.END)
        self.refresh_list()

    def show_status(self, message: str, es_error: bool = False) -> None:
        """
        Muestra mensajes informativos o de error en la parte inferior del formulario con colores temáticos.
        """
        color = self.COLOR_INDICADOR_ERROR if es_error else self.COLOR_INDICADOR_EXITO
        self.lbl_status.configure(text=message, text_color=color)
