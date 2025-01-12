import requests
from requests.auth import HTTPBasicAuth

# PayPal credentials

class PaypalClient:
    def __init__(self, mode="sandbox"):
        self.client_id = ##your paypal api info here
        self.client_secret = ##your paypal api info here
        self.api_url = f"https://api-m.{mode}.paypal.com"
        self.access_token = self.get_access_token()

    def get_access_token(self):
        auth_url = f"{self.api_url}/v1/oauth2/token"
        response = requests.post(auth_url,
                                 auth=HTTPBasicAuth(self.client_id, self.client_secret),
                                 data={"grant_type": "client_credentials"})
        response.raise_for_status()
        return response.json()["access_token"]

    def create_payment(self, username, total, currency, description, return_url, cancel_url):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        payment_data = {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{"amount": {"total": total, "currency": currency}, "custom": username, "description": description}],
            "redirect_urls": {"return_url": return_url, "cancel_url": cancel_url}
        }
        payment_url = f"{self.api_url}/v1/payments/payment"
        response = requests.post(payment_url, json=payment_data, headers=headers)
        response.raise_for_status()
        return response.json()

    def execute_payment(self, payment_id, payer_id):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        execute_url = f"{self.api_url}/v1/payments/payment/{payment_id}/execute"
        response = requests.post(execute_url, json={"payer_id": payer_id}, headers=headers)
        response.raise_for_status()
        return response.json()
