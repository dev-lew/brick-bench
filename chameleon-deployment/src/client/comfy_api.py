import threading
import random
from dataclasses import asdict, dataclass, field
from typing import Optional


class ComfyUINode:
    def __init__(self, node_id: str, inputs: dict, class_type: str, meta: dict) -> None:
        self.node_id = node_id
        self.inputs = inputs
        self.class_type = class_type
        self.meta = meta

    def to_json(self) -> dict:
        return {
            "inputs": self.inputs,
            "class_type": self.class_type,
            "_meta": self.meta,
        }


@dataclass
class KSamplerInput:
    seed: int = 1
    steps: int = 20
    cfg: float = 4.01
    sampler_name: str = "euler"
    scheduler: str = "sgm_uniform"
    denoise: int = 1
    model: list[str | int] = field(default_factory=lambda: ["4", 0])
    positive: list[str | int] = field(default_factory=lambda: ["16", 0])
    negative: list[str | int] = field(default_factory=lambda: ["40", 0])
    latent_image: list[str | int] = field(default_factory=lambda: ["53", 0])


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
            self.node_id,
            asdict(inputs),
            "CheckpointLoaderSimple",
            {"title": "Load Checkpoint"},
        )


@dataclass
class VAEDecodeInput:
    samples: list[str | int] = field(default_factory=lambda: ["3", 0])
    vae: list[str | int] = field(default_factory=lambda: ["4", 2])


class VAEDecode(ComfyUINode):
    node_id = "8"

    def __init__(self, inputs: VAEDecodeInput = VAEDecodeInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "VAEDecode", {"title": "VAE Decode"}
        )


@dataclass
class SaveImageInput:
    filename_prefix: str = "ComfyUI"
    images: list[str | int] = field(default_factory=lambda: ["8", 0])


class SaveImage(ComfyUINode):
    node_id = "9"

    def __init__(self, inputs: SaveImageInput = SaveImageInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "SaveImage", {"title": "Save Image"}
        )


@dataclass
class CLIPTextEncodeInput:
    text: str
    clip: list[str | int] = field(default_factory=lambda: ["55", 0])


class CLIPTextWords:
    words = []

    # We lock because many locust threads will be running this
    # code. We only need one to open the file and load the words.
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
            self.node_id, asdict(inputs), "CLIPTextEncode", {"title": "Positive Prompt"}
        )


class CLIPTextEncodeNegative(ComfyUINode):
    node_id = "40"

    def __init__(
        self, inputs: CLIPTextEncodeInput = CLIPTextEncodeInput(text="text")
    ) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "CLIPTextEncode", {"title": "Positive Prompt"}
        )


@dataclass
class EmptySD3LatentImageInput:
    width: int = 1024
    height: int = 1024
    batch_size: int = 1


class EmptySD3LatentImage(ComfyUINode):
    node_id = "53"

    def __init__(
        self, inputs: EmptySD3LatentImageInput = EmptySD3LatentImageInput()
    ) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "EmptySD3LatentImage",
            {"title": "EmptySD3LatentImage"},
        )


@dataclass
class TripleCLIPLoaderInput:
    clip_name1: str = "clip_g.safetensors"
    clip_name2: str = "clip_l.safetensors"
    clip_name3: str = "t5xxl_fp16.safetensors"


class TripleCLIPLoader(ComfyUINode):
    node_id = "55"

    def __init__(self, inputs: TripleCLIPLoaderInput = TripleCLIPLoaderInput()) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "TripleCLIPLoader",
            {"title": "TripleCLIPLoader"},
        )


class ComfyUIRequest:
    def __init__(
        self,
        ksampler: KSampler = KSampler(),
        load_checkpoint: LoadCheckpoint = LoadCheckpoint(),
        vae_decode: VAEDecode = VAEDecode(),
        save_image: SaveImage = SaveImage(),
        positive_prompt: CLIPTextEncodePositive = CLIPTextEncodePositive(),
        negative_prompt: CLIPTextEncodeNegative = CLIPTextEncodeNegative(),
        latent_image: EmptySD3LatentImage = EmptySD3LatentImage(),
        triple_clip_loader: TripleCLIPLoader = TripleCLIPLoader(),
    ) -> None:
        self.ksampler = ksampler
        self.load_checkpoint = load_checkpoint
        self.vae_decode = vae_decode
        self.save_image = save_image
        self.positive_prompt = positive_prompt
        self.negative_prompt = negative_prompt
        self.latent_image = latent_image
        self.triple_clip_loader = triple_clip_loader

    def generate_data(self) -> dict:
        return {
            self.ksampler.node_id: self.ksampler.to_json(),
            self.load_checkpoint.node_id: self.load_checkpoint.to_json(),
            self.vae_decode.node_id: self.vae_decode.to_json(),
            self.save_image.node_id: self.save_image.to_json(),
            self.positive_prompt.node_id: self.positive_prompt.to_json(),
            self.negative_prompt.node_id: self.negative_prompt.to_json(),
            self.latent_image.node_id: self.latent_image.to_json(),
            self.triple_clip_loader.node_id: self.triple_clip_loader.to_json(),
        }
