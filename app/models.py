"""Modelos de la base de datos: estudiantes, tareas y entregas."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")  # "student" o "teacher"

    submissions = relationship("Submission", back_populates="student")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    due_datetime = Column(DateTime, nullable=False)

    submissions = relationship("Submission", back_populates="task")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        # Garantiza a nivel de BD que un estudiante no pueda entregar dos veces la misma tarea
        UniqueConstraint("student_id", "task_id", name="unique_submission"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    submitted_at = Column(DateTime, nullable=False)

    student = relationship("Student", back_populates="submissions")
    task = relationship("Task", back_populates="submissions")