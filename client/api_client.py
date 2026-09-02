"""
لایه‌ی ارتباط با سرور. نکته‌ی امنیتی مهم: توکن ورود فقط در حافظه‌ی (RAM) همین
پردازه نگه داشته می‌شود و هرگز روی دیسک لپ‌تاپ ذخیره نمی‌شود. با بستن برنامه
توکن از بین می‌رود و کاربر باید دوباره وارد شود (یا در آینده از keyring برای
"مرا به خاطر بسپار" با محدودیت زمانی کوتاه استفاده کنید).
"""
import requests

from config import SERVER_URL


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    def __init__(self):
        self.token: str | None = None
        self.role: str | None = None
        self.full_name: str | None = None

    # ---------- Auth ----------
    def login(self, username: str, password: str):
        resp = requests.post(
            f"{SERVER_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if resp.status_code != 200:
            detail = resp.json().get("detail", "خطا در ورود") if resp.content else "خطا در ورود"
            raise ApiError(detail, resp.status_code)
        data = resp.json()
        self.token = data["access_token"]
        self.role = data["role"]
        self.full_name = data["full_name"]
        return data

    def logout(self):
        self.token = None
        self.role = None
        self.full_name = None

    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # ---------- Properties ----------
    def list_properties(self, **filters):
        resp = requests.get(f"{SERVER_URL}/properties/", params=filters, headers=self._headers, timeout=10)
        self._raise_for_status(resp)
        return resp.json()

    def upcoming_renewals(self, days: int = 30):
        resp = requests.get(
            f"{SERVER_URL}/properties/renewals", params={"days": days}, headers=self._headers, timeout=10
        )
        self._raise_for_status(resp)
        return resp.json()

    def create_property(self, payload: dict):
        resp = requests.post(f"{SERVER_URL}/properties/", json=payload, headers=self._headers, timeout=10)
        self._raise_for_status(resp)
        return resp.json()

    def update_property(self, property_id: int, payload: dict):
        resp = requests.put(
            f"{SERVER_URL}/properties/{property_id}", json=payload, headers=self._headers, timeout=10
        )
        self._raise_for_status(resp)
        return resp.json()

    def deactivate_property(self, property_id: int):
        resp = requests.delete(f"{SERVER_URL}/properties/{property_id}", headers=self._headers, timeout=10)
        self._raise_for_status(resp)
        return resp.json()

    # ---------- Property Images ----------
    def list_property_images(self, property_id: int):
        resp = requests.get(
            f"{SERVER_URL}/properties/{property_id}/images/", headers=self._headers, timeout=10
        )
        self._raise_for_status(resp)
        return resp.json()

    def upload_property_images(self, property_id: int, file_paths: list[str]):
        import mimetypes

        files = []
        opened = []
        try:
            for path in file_paths:
                content_type = mimetypes.guess_type(path)[0] or "image/jpeg"
                f = open(path, "rb")
                opened.append(f)
                filename = path.split("/")[-1].split("\\")[-1]
                files.append(("files", (filename, f, content_type)))
            resp = requests.post(
                f"{SERVER_URL}/properties/{property_id}/images/",
                files=files,
                headers=self._headers,
                timeout=60,
            )
        finally:
            for f in opened:
                f.close()
        self._raise_for_status(resp)
        return resp.json()

    def get_property_image_bytes(self, property_id: int, image_id: int) -> bytes:
        resp = requests.get(
            f"{SERVER_URL}/properties/{property_id}/images/{image_id}/file",
            headers=self._headers,
            timeout=15,
        )
        self._raise_for_status(resp)
        return resp.content

    def delete_property_image(self, property_id: int, image_id: int):
        resp = requests.delete(
            f"{SERVER_URL}/properties/{property_id}/images/{image_id}",
            headers=self._headers,
            timeout=10,
        )
        self._raise_for_status(resp)
        return resp.json()

    # ---------- Users (admin only) ----------
    def list_users(self):
        resp = requests.get(f"{SERVER_URL}/users/", headers=self._headers, timeout=10)
        self._raise_for_status(resp)
        return resp.json()

    def create_agent(self, username, full_name, password, role="agent"):
        resp = requests.post(
            f"{SERVER_URL}/users/",
            json={"username": username, "full_name": full_name, "password": password, "role": role},
            headers=self._headers,
            timeout=10,
        )
        self._raise_for_status(resp)
        return resp.json()

    def deactivate_user(self, user_id: int):
        resp = requests.post(f"{SERVER_URL}/users/{user_id}/deactivate", headers=self._headers, timeout=10)
        self._raise_for_status(resp)
        return resp.json()

    def activate_user(self, user_id: int):
        resp = requests.post(f"{SERVER_URL}/users/{user_id}/activate", headers=self._headers, timeout=10)
        self._raise_for_status(resp)
        return resp.json()

    def reset_user_password(self, user_id: int, new_password: str):
        resp = requests.post(
            f"{SERVER_URL}/users/{user_id}/reset-password",
            json={"new_password": new_password},
            headers=self._headers,
            timeout=10,
        )
        self._raise_for_status(resp)
        return resp.json()

    # ---------- Excel Import ----------
    def import_excel(self, file_path: str) -> dict:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.split("/")[-1].split("\\")[-1], f,
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            resp = requests.post(f"{SERVER_URL}/properties/import", files=files, headers=self._headers, timeout=60)
        self._raise_for_status(resp)
        return resp.json()

    def download_import_template(self, save_path: str):
        resp = requests.get(f"{SERVER_URL}/properties/import-template", headers=self._headers, timeout=15)
        self._raise_for_status(resp)
        with open(save_path, "wb") as f:
            f.write(resp.content)

    # ---------- Reports & Export ----------
    def _download_to_file(self, url: str, save_path: str, params: dict = None):
        resp = requests.get(url, params=params or {}, headers=self._headers, timeout=30)
        self._raise_for_status(resp)
        with open(save_path, "wb") as f:
            f.write(resp.content)

    def export_properties_pdf(self, save_path: str, **filters):
        self._download_to_file(f"{SERVER_URL}/properties/export/pdf", save_path, filters)

    def export_properties_excel(self, save_path: str, **filters):
        self._download_to_file(f"{SERVER_URL}/properties/export/excel", save_path, filters)

    def get_agent_performance(self):
        resp = requests.get(f"{SERVER_URL}/reports/agent-performance", headers=self._headers, timeout=15)
        self._raise_for_status(resp)
        return resp.json()

    def export_agent_performance_pdf(self, save_path: str):
        self._download_to_file(f"{SERVER_URL}/reports/agent-performance/pdf", save_path)

    # ---------- Version ----------
    def get_server_version(self):
        resp = requests.get(f"{SERVER_URL}/version", timeout=5)
        self._raise_for_status(resp)
        return resp.json()

    @staticmethod
    def _raise_for_status(resp: requests.Response):
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", "خطای نامشخص")
            except Exception:
                detail = "خطای نامشخص"
            raise ApiError(detail, resp.status_code)


api_client = ApiClient()  # نمونه‌ی مشترک در کل برنامه‌ی کلاینت
