import requests
from typing import Dict, Any


class AnalyticsClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url

    def analyze(self, query: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/analyze",
                json=query,
                timeout=5
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Analytics service error: {str(e)}"
            }