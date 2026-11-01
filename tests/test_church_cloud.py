# -*- coding: utf-8 -*-
"""
Tests for ArchiveMaster ChurchAI Mobile Cloud & Telegram Server
"""

import pytest
from starlette.testclient import TestClient
from modules.church_cloud_server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_pwa_manifest(client):
    res = client.get("/manifest.json")
    assert res.status_code == 200
    data = res.json()
    assert data["short_name"] == "ChurchAI"
    assert data["display"] == "standalone"


def test_pwa_index_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "ChurchAI Cloud" in res.text
    assert "وضع المنبر" in res.text


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "version" in data


def test_api_stats(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_books" in data
    assert "total_pages" in data


def test_api_search(client):
    res = client.get("/api/search?q=الآباء&limit=3")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert "total_hits" in data


def test_api_ask(client):
    res = client.post("/api/ask", json={"question": "الصلاة الدائمة", "limit": 2})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "sources" in data
