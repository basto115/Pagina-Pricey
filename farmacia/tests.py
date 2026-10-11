from django.test import TestCase, Client
from django.urls import reverse

from .models import Medicamento, Farmacia, Precio

# Create your tests here.

class APITestCase(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.medicamento = Medicamento.objects.create(
            nombre="Paracetamol",
            principio_activo="Paracetamol"
        )
    
    def setUp(self):
        self.cliente = Client()
    
    def test_api_medicamentos_responde_correctamente(self):
        respuesta = self.cliente.get("/api/medicamentos/")
    
        self.assertEqual(respuesta.status_code, 200)
    
    def test_api_medicamentos_rechaza_post(self):
        respuesta = self.cliente.post("/api/medicamentos/")
        
        self.assertEqual(respuesta.status_code, 405)
        
    def test_api_medicamentos_devuelve_lista_json(self):
        respuesta = self.cliente.get("/api/medicamentos/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        
        datos = respuesta.json()
        
        self.assertIsInstance(datos, list)
        self.assertTrue(
            any(
                medicamento["nombre"] == "Paracetamol"
                for medicamento in datos
            )
        )
    
    def test_api_farmacias_responde_correctamente(self):
        respuesta = self.cliente.get("/api/farmacias/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("farmacias", respuesta.json())

    def test_api_farmacias_rechaza_post(self):
        respuesta = self.cliente.post("/api/farmacias/")

        self.assertEqual(respuesta.status_code, 405)

    def test_api_precios_responde_correctamente(self):
        respuesta = self.cliente.get("/api/precios/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("precios", respuesta.json())

    def test_api_precios_rechaza_post(self):
        respuesta = self.cliente.post("/api/precios/")

        self.assertEqual(respuesta.status_code, 405)