"""
Pruebas de carga con Locust para TaskHub.

Ejecutar:
    pip install locust
    locust -f tests/load-test.py --host=http://localhost

Luego abrir http://localhost:8089, definir el número de usuarios concurrentes
y la tasa de generación ("spawn rate"), e iniciar la prueba.

Nota: el usuario de prueba se crea con app/seed.py (demo@epn.edu.ec / 123456).
Para una prueba más realista con muchos estudiantes distintos en paralelo,
conviene sembrar varios registros de estudiantes en la base de datos.
"""
import random
from locust import HttpUser, task, between

class StudentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # LOGIN CORRECTO (según tu código real)
        self.client.post("/login", data={
            "email": "demo@epn.edu.ec",
            "password": "123456",
        })

    @task(3)
    def view_tasks(self):
        self.client.get("/tasks", name="/tasks [listado]")

    @task(2)
    def view_task_detail(self):
        task_id = random.choice([1, 2])
        self.client.get(f"/tasks/{task_id}", name="/tasks/[id]")

    @task(1)
    def submit_task(self):
        task_id = random.choice([1, 2])
        self.client.post(
            f"/tasks/{task_id}/submit",
            data={"response_text": "Respuesta de prueba"},
            name="/tasks/[id]/submit",
        )

    @task(1)
    def check_node(self):
        self.client.get("/health", name="/health")
