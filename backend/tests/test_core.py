"""
集成测试 — API 端点测试
需要数据库初始化（运行前确保 database.db 可写）
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def test_learning_engine_init():
    """测试学习引擎初始化"""
    from core.learning_crew import LearningEngine
    engine = LearningEngine(session_id=1, student_id="test_student")
    assert engine.session_id == 1
    assert engine.student_id == "test_student"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
