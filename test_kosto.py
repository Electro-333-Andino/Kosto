"""
test_kosto.py

Suite de pruebas unitarias para Kosto.
Verifica la lógica de negocio (dominio) y las operaciones de persistencia (infraestructura SQLite3).
Utiliza 'unittest' de la librería estándar de Python.
"""

import os
import sqlite3
import unittest
from decimal import Decimal

from domain.models import Producto
from infrastructure.database import DatabaseManager


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
            costo_total=3.67,
            unidades_por_paquete=12,
            precio_manual=0.35,
        )
        # 3.67 / 12 = 0.305833... -> redondeado a 4 decimales: 0.3058
        self.assertEqual(p.costo_unitario_real, Decimal("0.3058"))
        # Costo unitario real (0.3058) redondeado a 2 decimales: 0.31
        self.assertEqual(p.precio_sugerido, Decimal("0.31"))
        # Ganancia: 0.35 - 0.3058 = 0.0442
        self.assertEqual(p.ganancia_neta, Decimal("0.0442"))

    def test_precio_manual_por_defecto_sugerido(self) -> None:
        """
        Verifica que si no se proporciona un precio manual, este tome el valor del precio sugerido,
        y calcule la ganancia correspondiente.
        """
        p = Producto(
            nombre="Harina de Trigo", costo_total=10.00, unidades_por_paquete=10
        )
        self.assertEqual(p.costo_unitario_real, Decimal("1.0000"))
        self.assertEqual(p.precio_sugerido, Decimal("1.00"))
        self.assertEqual(p.precio_manual, Decimal("1.00"))
        self.assertEqual(p.ganancia_neta, Decimal("0.00"))

    def test_actualizar_precio_manual_exito(self) -> None:
        """
        Verifica que al actualizar el precio manual, la ganancia neta se recalcule de forma correcta.
        """
        p = Producto(
            nombre="Salsa de Tomate", costo_total=5.00, unidades_por_paquete=10
        )
        # Costo real = 0.50, Sugerido = 0.50, Manual Inicial = 0.50, Ganancia Inicial = 0.00
        p.update_precio_manual(0.75)
        self.assertEqual(p.precio_manual, Decimal("0.75"))
        # Ganancia: 0.75 - 0.50 = 0.25
        self.assertEqual(p.ganancia_neta, Decimal("0.25"))

    def test_validaciones_valores_invalidos(self) -> None:
        """
        Verifica que el modelo de dominio rechace valores inválidos en la creación.
        """
        # Nombre vacío
        with self.assertRaises(ValueError):
            Producto(nombre="", costo_total=10.00, unidades_por_paquete=10)

        # Costo total <= 0
        with self.assertRaises(ValueError):
            Producto(nombre="Arroz", costo_total=0.0, unidades_por_paquete=10)
        with self.assertRaises(ValueError):
            Producto(nombre="Arroz", costo_total=-1.5, unidades_por_paquete=10)

        # Unidades por paquete <= 0
        with self.assertRaises(ValueError):
            Producto(nombre="Fideos", costo_total=5.0, unidades_por_paquete=0)
        with self.assertRaises(ValueError):
            Producto(nombre="Fideos", costo_total=5.0, unidades_por_paquete=-5)

        # Precio manual negativo
        with self.assertRaises(ValueError):
            Producto(
                nombre="Fideos",
                costo_total=5.0,
                unidades_por_paquete=5,
                precio_manual=-0.5,
            )

    def test_actualizar_precio_manual_invalido(self) -> None:
        """
        Verifica que no se permita establecer un precio manual negativo.
        """
        p = Producto(nombre="Leche", costo_total=4.50, unidades_por_paquete=5)
        with self.assertRaises(ValueError):
            p.update_precio_manual(-0.1)


class TestDatabaseManager(unittest.TestCase):
    """
    Pruebas de integración para el Administrador de Base de Datos.
    Utiliza una base de datos SQLite3 en memoria para garantizar aislamiento e idoneidad.
    """

    def setUp(self) -> None:
        # Inicializar base de datos limpia en memoria para cada prueba
        self.db = DatabaseManager(":memory:")

    def tearDown(self) -> None:
        # Cerrar la conexión para evitar fugas de descriptores de archivos
        self.db.cerrar_conexion()

    def test_db_inicializacion(self) -> None:
        """
        Verifica que la tabla productos se cree correctamente.
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='productos'"
        )
        table_exists = cursor.fetchone()
        self.assertIsNotNone(table_exists)

    def test_insertar_y_obtener_producto_exito(self) -> None:
        """
        Verifica que un producto se inserte correctamente y se asigne un ID secuencial.
        """
        p = Producto(
            nombre="Azúcar 1kg",
            costo_total=12.50,
            unidades_por_paquete=10,
            precio_manual=1.50,
        )
        self.assertIsNone(p.id)

        # Guardar en base de datos
        p_guardado = self.db.insertar_producto(p)
        self.assertIsNotNone(p_guardado.id)
        self.assertEqual(p_guardado.id, 1)

        # Recuperar de la base de datos
        productos = self.db.obtener_productos()
        self.assertEqual(len(productos), 1)

        prod_recuperado = productos[0]
        self.assertEqual(prod_recuperado.id, p_guardado.id)
        self.assertEqual(prod_recuperado.nombre, "Azúcar 1kg")
        self.assertEqual(prod_recuperado.costo_total, Decimal("12.50"))
        self.assertEqual(prod_recuperado.unidades_por_paquete, 10)
        self.assertEqual(prod_recuperado.precio_manual, Decimal("1.50"))

        # Comprobar que los campos calculados se recalcularon correctamente al recuperar
        self.assertEqual(prod_recuperado.costo_unitario_real, Decimal("1.2500"))
        self.assertEqual(prod_recuperado.precio_sugerido, Decimal("1.25"))
        self.assertEqual(prod_recuperado.ganancia_neta, Decimal("0.2500"))

    def test_actualizar_producto_exito(self) -> None:
        """
        Verifica la actualización correcta de campos en la base de datos.
        """
        p = Producto(nombre="Café Soluble", costo_total=8.00, unidades_por_paquete=4)
        p_guardado = self.db.insertar_producto(p)

        # Modificar producto
        p_guardado.nombre = "Café Soluble Premium"
        p_guardado.update_precio_manual(
            3.00
        )  # Costo unitario real = 2.00, ganancia = 1.00

        self.db.actualizar_producto(p_guardado)

        # Recuperar y verificar
        productos = self.db.obtener_productos()
        self.assertEqual(len(productos), 1)
        p_act = productos[0]
        self.assertEqual(p_act.nombre, "Café Soluble Premium")
        self.assertEqual(p_act.precio_manual, Decimal("3.00"))
        self.assertEqual(p_act.ganancia_neta, Decimal("1.00"))

    def test_obtener_productos_con_filtro_busqueda(self) -> None:
        """
        Verifica que el buscador filtre productos correctamente por coincidencia parcial y segura (LIKE).
        """
        p1 = Producto(nombre="Manzana Roja", costo_total=5.00, unidades_por_paquete=5)
        p2 = Producto(nombre="Manzana Verde", costo_total=6.00, unidades_por_paquete=5)
        p3 = Producto(
            nombre="Plátano Tabasco", costo_total=3.00, unidades_por_paquete=6
        )

        self.db.insertar_producto(p1)
        self.db.insertar_producto(p2)
        self.db.insertar_producto(p3)

        # Buscar "Manzana" (debería retornar 2 productos)
        resultados = self.db.obtener_productos(busqueda="Manzana")
        self.assertEqual(len(resultados), 2)
        nombres = [r.nombre for r in resultados]
        self.assertIn("Manzana Roja", nombres)
        self.assertIn("Manzana Verde", nombres)

        # Buscar "verde" (case-insensitive parcial)
        resultados_verde = self.db.obtener_productos(busqueda="verde")
        self.assertEqual(len(resultados_verde), 1)
        self.assertEqual(resultados_verde[0].nombre, "Manzana Verde")

        # Buscar algo que no existe
        resultados_nulos = self.db.obtener_productos(busqueda="Naranja")
        self.assertEqual(len(resultados_nulos), 0)

    def test_eliminar_producto_exito(self) -> None:
        """
        Verifica la eliminación correcta de un registro.
        """
        p = Producto(nombre="Yogur Griego", costo_total=4.00, unidades_por_paquete=4)
        p_guardado = self.db.insertar_producto(p)
        self.assertEqual(len(self.db.obtener_productos()), 1)

        # Eliminar
        self.db.eliminar_producto(p_guardado.id)
        self.assertEqual(len(self.db.obtener_productos()), 0)


if __name__ == "__main__":
    unittest.main()
