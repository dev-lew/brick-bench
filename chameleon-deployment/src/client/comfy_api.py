import json
import threading
import random
from dataclasses import asdict, dataclass
from typing import Optional


class ComfyUINode:
    def __init__(self, node_id: str, inputs: dict, class_type: str, meta: dict) -> None:
        self.node_id = node_id
        self.inputs = inputs
        self.class_type = class_type
        self.meta = meta

    def to_json(self) -> str:
        return json.dumps(
            {
                self.node_id: self.inputs,
                "class_type": self.class_type,
                "_meta": self.meta,
            }
        )


@dataclass
class KSamplerInput:
    seed: int = 1
    steps: int = 20
    cfg: float = 4.01
    sampler_name: str = "euler"
    scheduler: str = "sgm_uniform"
    denoise: int = 1
    model: list[str | int] = ["4", 0]
    positive: list[str | int] = ["16", 0]
    negative: list[str | int] = ["40", 0]
    latent_image: list[str | int] = ["53", 0]


class KSampler(ComfyUINode):
    node_id = "3"

    def __init__(self, inputs: KSamplerInput = KSamplerInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "KSampler", {"title": "KSampler"}
        )


@dataclass
class LoadCheckpointInput:
    ckpt_name: str = "sd3.5_large.safetensors"


class LoadCheckpoint(ComfyUINode):
    node_id = "4"

    def __init__(self, inputs: LoadCheckpointInput = LoadCheckpointInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "LoadCheckpoint", {"title": "Load Checkpoint"}
        )


@dataclass
class VAEDecodeInput:
    samples: list[str | int] = ["3", 0]
    vae: list[str | int] = ["4", 2]


class VAEDecode(ComfyUINode):
    node_id = "8"

    def __init__(self, inputs: VAEDecodeInput = VAEDecodeInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "VAEDecode", {"title": "VAE Decode"}
        )


@dataclass
class SaveImageInput:
    filename_prefix: str = "ComfyUI"
    images: list[str | int] = ["8", 0]


class SaveImage(ComfyUINode):
    node_id = "9"

    def __init__(self, inputs: SaveImageInput = SaveImageInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "SaveImage", {"title": "Save Image"}
        )


@dataclass
class CLIPTextEncodeInput:
    text: str
    clip: list[str | int] = ["55", 0]


class CLIPTextWords:
    words = []
    _lock = threading.Lock()

    def __init__(self):
        if not CLIPTextWords.words:
            with CLIPTextWords._lock:
                if not CLIPTextWords.words:
                    self._load_words()

    def _load_words(self, filepath: str = "/usr/share/dict/words"):
        with open(filepath, "r") as f:
            CLIPTextWords.words = [word.strip() for word in f.readlines()]

    def generate_prompt(self, num_words: int = 10):
        return " ".join(random.sample(CLIPTextWords.words, num_words))


class CLIPTextEncodePositive(ComfyUINode):
    node_id = "16"
    words = CLIPTextWords()

    def __init__(self, inputs: Optional[CLIPTextEncodeInput] = None) -> None:
        if inputs is None:
            inputs = CLIPTextEncodeInput(
                text=CLIPTextEncodePositive.words.generate_prompt()
            )

        super().__init__(
            self.node_id, asdict(inputs), "ClipTextEncode", {"title": "Positive Prompt"}
        )


class CLIPTextEncodeNegative(ComfyUINode):
    node_id = "40"

    def __init__(
        self, inputs: CLIPTextEncodeInput = CLIPTextEncodeInput(text="text")
    ) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "CLIPTextEncode", {"title": "Positive Prompt"}
        )
