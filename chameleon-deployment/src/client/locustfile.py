from comfy_api import ComfyUIRequest
from locust import HttpUser, task


class GenerateImageRequest(HttpUser):
    hostname = "stable-diffusion-comfy-ui.brick-bench.svc.cluster.local"

    @task
    def generate_image(self):
        self.client.post(self.hostname, data=ComfyUIRequest())
