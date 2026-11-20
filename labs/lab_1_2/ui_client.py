"""HTTP-only client shared by Streamlit pages. No direct database access."""
import os
import requests


class ApiError(Exception):
    """A user-readable HTTP, validation, or connection failure."""


class ApiClient:
    def __init__(self, base_url=None):
        self.base_url = (base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000")).rstrip("/")

    def request(self, method, path, *, params=None, json=None):
        try:
            response = requests.request(method, self.base_url + path, params=params, json=json, timeout=(3, 10))
        except requests.RequestException:
            raise ApiError("Серверге қосылу мүмкін болмады. Байланысты тексеріп, тізімді жаңартыңыз. "
                           "Сақтау сұрауын қайталамас бұрын тапсырыстың қосылғанын тексеріңіз.") from None
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
            if isinstance(detail, list):
                messages = []
                for item in detail:
                    if isinstance(item, dict):
                        field = ".".join(str(part) for part in item.get("loc", []) if part != "body")
                        messages.append(f"{field}: {item.get('msg', 'мәнді тексеріңіз')}")
                detail = "; ".join(messages)
            if response.status_code >= 500:
                detail = "Серверде қате болды. Өзгерісті қайталамас бұрын тізімді жаңартыңыз."
            if not isinstance(detail, str) or not detail:
                detail = "Сұрау орындалмады. Енгізілген деректерді тексеріңіз."
            raise ApiError(f"{detail} (HTTP {response.status_code})")
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError:
            raise ApiError("Сервер жауабын оқу мүмкін болмады. Қайта сақтамас бұрын тізімді жаңартыңыз.") from None
