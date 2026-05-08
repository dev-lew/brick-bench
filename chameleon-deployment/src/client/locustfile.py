import os

from comfy_api import ImageRequest, ImageToVideoRequest
from locust import HttpUser, constant_pacing, task

DEFAULT_WAIT_TIME = 30.0


class ImageGenerationUser(HttpUser):
    host = "http://stable-diffusion-comfy-ui.brick-bench.svc.cluster.local"
    fixed_count = int(os.getenv("IMAGE_GEN_USERS", 1))
    wait_time = constant_pacing(float(os.getenv("WAIT_TIME", DEFAULT_WAIT_TIME)))

    @task
    def generate_image(self):
        self.client.post(
            "/prompt",
            json=ImageRequest().generate_data(),
        )


class ImageToVideoGenerationUser(HttpUser):
    host = "http://wan-comfy-ui.brick-bench.svc.cluster.local"
    fixed_count = int(os.getenv("IMAGE_TO_VIDEO_USERS", 1))
    wait_time = constant_pacing(float(os.getenv("WAIT_TIME", DEFAULT_WAIT_TIME)))

    @task
    def generate_video(self):
        self.client.post(
            "/prompt",
            json=ImageToVideoRequest().generate_data(),
        )
