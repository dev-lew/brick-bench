import random
import threading
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


@dataclass
class SaveAnimatedWEBPInput:
    filename_prefix: str = "ComfyUI"
    fps: int = 16
    lossless: bool = False
    quality: int = 50
    method: str = "default"
    images: list[str | int] = field(default_factory=lambda: ["8", 0])


class SaveAnimatedWEBP(ComfyUINode):
    node_id = "28"

    def __init__(self, inputs: SaveAnimatedWEBPInput = SaveAnimatedWEBPInput()) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "SaveAnimatedWEBP",
            {"title": "SaveAnimatedWEBP"},
        )


@dataclass
class UNETLoaderInput:
    unet_name: str = "split_files/diffusion_models/wan2.1_i2v_480p_14B_fp16.safetensors"
    weight_dtype: str = "default"


class UNETLoader(ComfyUINode):
    node_id = "37"

    def __init__(self, inputs: UNETLoaderInput = UNETLoaderInput()) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "UNETLoader",
            {"title": "Load Diffusion Model"},
        )


@dataclass
class CLIPLoaderInput:
    clip_name: str = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    type: str = "wan"
    device: str = "default"


class CLIPLoader(ComfyUINode):
    node_id = "38"

    def __init__(self, inputs: CLIPLoaderInput = CLIPLoaderInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "CLIPLoader", {"title": "Load CLIP"}
        )


@dataclass
class VAELoaderInput:
    vae_name: str = "split_files/vae/wan_2.1_vae.safetensors"


class VAELoader(ComfyUINode):
    node_id = "39"

    def __init__(self, inputs: VAELoaderInput = VAELoaderInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "VAELoader", {"title": "Load VAE"}
        )


@dataclass
class CLIPVisionLoaderInput:
    clip_name: str = "split_files/clip_vision/clip_vision_h.safetensors"


class CLIPVisionLoader(ComfyUINode):
    node_id = "49"

    def __init__(self, inputs: CLIPVisionLoaderInput = CLIPVisionLoaderInput()) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "CLIPVisionLoader",
            {"title": "Load CLIP Vision"},
        )


@dataclass
class WanImageToVideoInput:
    width: int = 256
    height: int = 256
    length: int = 61
    batch_size: int = 1
    positive: list[str | int] = field(default_factory=lambda: ["6", 0])
    negative: list[str | int] = field(default_factory=lambda: ["7", 0])
    vae: list[str | int] = field(default_factory=lambda: ["39", 0])
    clip_vision_output: list[str | int] = field(default_factory=lambda: ["51", 0])
    start_image: list[str | int] = field(default_factory=lambda: ["52", 0])


class WanImageToVideo(ComfyUINode):
    node_id = "50"

    def __init__(self, inputs: WanImageToVideoInput = WanImageToVideoInput()) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "WanImageToVideo",
            {"title": "WanImageToVideo"},
        )


@dataclass
class CLIPVisionEncodeInput:
    crop: str = "none"
    clip_vision: list[str | int] = field(default_factory=lambda: ["49", 0])
    image: list[str | int] = field(default_factory=lambda: ["52", 0])


class CLIPVisionEncode(ComfyUINode):
    node_id = "51"

    def __init__(self, inputs: CLIPVisionEncodeInput = CLIPVisionEncodeInput()) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "CLIPVisionEncode",
            {"title": "CLIP Vision Encode"},
        )


@dataclass
class LoadImageInput:
    image: str = "data/default.png"


class LoadImage(ComfyUINode):
    node_id = "52"

    def __init__(self, inputs: LoadImageInput = LoadImageInput()) -> None:
        super().__init__(
            self.node_id, asdict(inputs), "LoadImage", {"title": "Load Image"}
        )


@dataclass
class ModelSamplingSD3Input:
    shift: int = 8
    model: list[str | int] = field(default_factory=lambda: ["37", 0])


class ModelSamplingSD3(ComfyUINode):
    node_id = "54"

    def __init__(self, inputs: ModelSamplingSD3Input = ModelSamplingSD3Input()) -> None:
        super().__init__(
            self.node_id,
            asdict(inputs),
            "ModelSamplingSD3",
            {"title": "ModelSamplingSD3"},
        )


class ImageToVideoRequest:
    def __init__(
        self,
        clip_loader: CLIPLoader = CLIPLoader(),
        clip_vision_encode: CLIPVisionEncode = CLIPVisionEncode(),
        clip_vision_loader: CLIPVisionLoader = CLIPVisionLoader(),
        ksampler: KSampler = KSampler(),
        load_image: LoadImage = LoadImage(),
        model_sampling_sd3: ModelSamplingSD3 = ModelSamplingSD3(),
        negative_prompt: CLIPTextEncodeNegative = CLIPTextEncodeNegative(),
        positive_prompt: CLIPTextEncodePositive = CLIPTextEncodePositive(),
        save_animated_webp: SaveAnimatedWEBP = SaveAnimatedWEBP(),
        unet_loader: UNETLoader = UNETLoader(),
        vae_decode: VAEDecode = VAEDecode(),
        vae_loader: VAELoader = VAELoader(),
        wan_image_to_video: WanImageToVideo = WanImageToVideo(),
    ) -> None:
        self.ksampler = ksampler
        self.positive_prompt = positive_prompt
        self.negative_prompt = negative_prompt
        self.vae_decode = vae_decode
        self.save_animated_webp = save_animated_webp
        self.unet_loader = unet_loader
        self.clip_loader = clip_loader
        self.vae_loader = vae_loader
        self.clip_vision_loader = clip_vision_loader
        self.wan_image_to_video = wan_image_to_video
        self.clip_vision_encode = clip_vision_encode
        self.load_image = load_image
        self.model_sampling_sd3 = model_sampling_sd3

    def generate_data(self) -> dict:
        return {
            self.ksampler.node_id: self.ksampler.to_json(),
            self.positive_prompt.node_id: self.positive_prompt.to_json(),
            self.negative_prompt.node_id: self.negative_prompt.to_json(),
            self.vae_decode.node_id: self.vae_decode.to_json(),
            self.save_animated_webp.node_id: self.save_animated_webp.to_json(),
            self.unet_loader.node_id: self.unet_loader.to_json(),
            self.clip_loader.node_id: self.clip_loader.to_json(),
            self.vae_loader.node_id: self.vae_loader.to_json(),
            self.clip_vision_loader.node_id: self.clip_vision_loader.to_json(),
            self.wan_image_to_video.node_id: self.wan_image_to_video.to_json(),
            self.clip_vision_encode.node_id: self.clip_vision_encode.to_json(),
            self.load_image.node_id: self.load_image.to_json(),
            self.model_sampling_sd3.node_id: self.model_sampling_sd3.to_json(),
        }


class ImageRequest:
    def __init__(
        self,
        ksampler: KSampler = KSampler(),
        latent_image: EmptySD3LatentImage = EmptySD3LatentImage(),
        load_checkpoint: LoadCheckpoint = LoadCheckpoint(),
        negative_prompt: CLIPTextEncodeNegative = CLIPTextEncodeNegative(),
        positive_prompt: CLIPTextEncodePositive = CLIPTextEncodePositive(),
        save_image: SaveImage = SaveImage(),
        triple_clip_loader: TripleCLIPLoader = TripleCLIPLoader(),
        vae_decode: VAEDecode = VAEDecode(),
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
