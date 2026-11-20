"""Read-only load against the isolated lab API; no external services or real accounts."""
from locust import HttpUser, between, task


class CargoReader(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(3)
    def list_orders(self):
        self.client.get('/api/orders?limit=20', name='/api/orders (20 rows)')

    @task(2)
    def search(self):
        self.client.get('/api/orders?search=LOAD&min_price=100000&limit=20', name='/api/orders (search + price)')

    @task(1)
    def detail(self):
        self.client.get('/api/orders/1', name='/api/orders/{id}')

    @task(1)
    def catalogs(self):
        self.client.get('/api/catalogs')
