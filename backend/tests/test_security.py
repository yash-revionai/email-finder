import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router as auth_router
from app.core.config import settings
from app.core.security import create_access_token, get_current_user


class SecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.password_patcher = patch.object(settings, "app_password", "phase6-password")
        self.secret_patcher = patch.object(settings, "jwt_secret", "phase6-secret")
        self.expiry_patcher = patch.object(settings, "access_token_expire_minutes", 60)

        self.password_patcher.start()
        self.secret_patcher.start()
        self.expiry_patcher.start()

        app = FastAPI()
        app.include_router(auth_router)

        @app.get("/protected")
        def protected(current_user: str = Depends(get_current_user)) -> dict[str, str]:
            return {"current_user": current_user}

        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.expiry_patcher.stop()
        self.secret_patcher.stop()
        self.password_patcher.stop()

    def test_token_route_returns_bearer_token(self) -> None:
        response = self.client.post("/api/auth/token", json={"password": "phase6-password"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["token_type"], "bearer")
        self.assertIn("access_token", payload)
        self.assertGreater(payload["expires_in"], 0)

    def test_token_route_rejects_invalid_password(self) -> None:
        response = self.client.post("/api/auth/token", json={"password": "wrong-password"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid password")

    def test_protected_route_requires_valid_bearer_token(self) -> None:
        response = self.client.get("/protected")
        self.assertEqual(response.status_code, 401)

        token = create_access_token({"sub": "operator"})
        authorized = self.client.get("/protected", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(authorized.status_code, 200)
        self.assertEqual(authorized.json()["current_user"], "operator")
