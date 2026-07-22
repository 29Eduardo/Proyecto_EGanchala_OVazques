"""
Pruebas de carga con Locust para TaskHub.

Ejecutar:
    pip install locust
    locust -f tests/load-test.py --host=http://localhost

Luego abrir http://localhost:8089, definir el número de usuarios concurrentes
y la tasa de generación ("spawn rate"), e iniciar la prueba.

"""
import random

from locust import HttpUser, task, between


class StudentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Cada usuario virtual inicia sesión una sola vez, igual que un estudiante real."""
        self.client.post("/login", data={
            "email": "demo@epn.edu.ec",
            "password": "123456",
        })

    @task(3)
    def view_tasks(self):
        """Consultar el listado de tareas disponibles."""
        self.client.get("/tasks", name="/tasks [listado]")

    @task(2)
    def view_task_detail(self):
        """Consultar el detalle de una tarea específica."""
        task_id = random.choice([1, 2])
        self.client.get(f"/tasks/{task_id}", name="/tasks/[id]")

    @task(1)
    def submit_task(self):
        """Intentar enviar una entrega (solo la primera vez tendrá éxito por estudiante/tarea)."""
        task_id = random.choice([1, 2])
        self.client.post(
            f"/tasks/{task_id}/submit",
            data={"response_text": "Respuesta generada durante la prueba de carga."},
            name="/tasks/[id]/submit",
        )

    @task(1)
    def check_node(self):
        """Permite verificar en los resultados qué nodo (app1/app2/app3) atendió cada petición."""
        self.client.get("/health", name="/health")
