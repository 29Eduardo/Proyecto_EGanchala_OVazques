import sys
import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from main import validate_password, current_student
from models import Student, Task, Submission, Assignment
from database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestPasswordValidation(unittest.TestCase):
    def test_too_short(self):
        self.assertEqual(validate_password("Short1!"), "La contraseña debe tener al menos 8 caracteres.")

    def test_missing_uppercase(self):
        self.assertEqual(validate_password("lowercase1!"), "La contraseña debe incluir al menos una letra mayúscula.")

    def test_missing_lowercase(self):
        self.assertEqual(validate_password("UPPERCASE1!"), "La contraseña debe incluir al menos una letra minúscula.")

    def test_missing_number(self):
        self.assertEqual(validate_password("NoNumberHere!"), "La contraseña debe incluir al menos un número.")

    def test_missing_special_char(self):
        self.assertEqual(validate_password("NoSpecialChar123"), "La contraseña debe incluir al menos un carácter especial (ej. !@#$%^&*).")

    def test_valid_passwords(self):
        self.assertIsNone(validate_password("ValidPassword123!"))
        self.assertIsNone(validate_password("Admin2026#"))
        self.assertIsNone(validate_password("P@ssw0rd99"))


class TestModelsAndRoles(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_student_roles(self):
        s1 = Student(full_name="Estudiante Demo", email="s1@epn.edu.ec", password_hash="hash", role="student")
        t1 = Student(full_name="Profesor Demo", email="t1@epn.edu.ec", password_hash="hash", role="teacher")
        a1 = Student(full_name="Admin Demo", email="a1@epn.edu.ec", password_hash="hash", role="admin")
        a2 = Student(full_name="Admin Demo 2", email="a2@epn.edu.ec", password_hash="hash", role="administrador")

        self.db.add_all([s1, t1, a1, a2])
        self.db.commit()

        self.assertEqual(s1.role, "student")
        self.assertEqual(t1.role, "teacher")
        self.assertEqual(a1.role, "admin")
        self.assertEqual(a2.role, "administrador")

    def test_cascade_delete_task(self):
        s1 = Student(full_name="Estudiante Demo", email="s1@epn.edu.ec", password_hash="hash", role="student")
        task = Task(code="TSK-100", title="Test Task", description="Desc", due_datetime=s1.id and None or s1.id)
        from datetime import datetime
        task.due_datetime = datetime.now()
        self.db.add_all([s1, task])
        self.db.commit()

        sub = Submission(student_id=s1.id, task_id=task.id, response_text="Answer", submitted_at=datetime.now())
        ass = Assignment(student_id=s1.id, task_id=task.id, assigned_at=datetime.now())
        self.db.add_all([sub, ass])
        self.db.commit()

        self.assertEqual(self.db.query(Submission).count(), 1)
        self.assertEqual(self.db.query(Assignment).count(), 1)

        # Eliminar tarea debe eliminar entregas y asignaciones en cascada
        self.db.delete(task)
        self.db.commit()

        self.assertEqual(self.db.query(Submission).count(), 0)
        self.assertEqual(self.db.query(Assignment).count(), 0)

if __name__ == "__main__":
    unittest.main()
