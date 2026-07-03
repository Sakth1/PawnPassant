from __future__ import annotations

import platform
from dataclasses import dataclass, field
from typing import ClassVar


BACKEND_BLAS = "blas"
BACKEND_CUDA = "cuda"
BACKEND_CUDNN = "cudnn"
BACKEND_DXIL = "dxil"
BACKEND_TENSORRT = "tensorrt"
BACKEND_ONNX = "onnx"
BACKEND_OPENCL = "opencl"


@dataclass(frozen=True)
class Lc0BackendInfo:
    id: str
    label: str
    description: str
    requires_gpu: bool = False
    requires_nvidia: bool = False
    platforms: tuple[str, ...] = ("windows", "linux")


ALL_BACKENDS: dict[str, Lc0BackendInfo] = {
    BACKEND_BLAS: Lc0BackendInfo(
        id=BACKEND_BLAS,
        label="CPU (OpenBLAS)",
        description="CPU-only via OpenBLAS. Widest compatibility, no GPU needed.",
        platforms=("windows", "macos", "linux", "android"),
    ),
    BACKEND_CUDA: Lc0BackendInfo(
        id=BACKEND_CUDA,
        label="CUDA 12 (NVIDIA)",
        description="NVIDIA GPU via CUDA 12. Requires compatible GPU + CUDA 12 runtime.",
        requires_gpu=True,
        requires_nvidia=True,
    ),
    BACKEND_CUDNN: Lc0BackendInfo(
        id=BACKEND_CUDNN,
        label="cuDNN (NVIDIA)",
        description="NVIDIA GPU via cuDNN. Faster than plain CUDA. Requires cuDNN installed.",
        requires_gpu=True,
        requires_nvidia=True,
    ),
    BACKEND_DXIL: Lc0BackendInfo(
        id=BACKEND_DXIL,
        label="DirectML (Any GPU)",
        description="Any DirectX 12 GPU via Microsoft DirectML. No CUDA needed.",
        requires_gpu=True,
        platforms=("windows",),
    ),
    BACKEND_TENSORRT: Lc0BackendInfo(
        id=BACKEND_TENSORRT,
        label="TensorRT (NVIDIA)",
        description="NVIDIA GPU via TensorRT. Fastest option. Requires TensorRT installed.",
        requires_gpu=True,
        requires_nvidia=True,
        platforms=("windows", "linux"),
    ),
    BACKEND_ONNX: Lc0BackendInfo(
        id=BACKEND_ONNX,
        label="ONNX Runtime",
        description="Any GPU via ONNX Runtime. Supports CUDA, DirectML, OpenVINO.",
        requires_gpu=True,
    ),
    BACKEND_OPENCL: Lc0BackendInfo(
        id=BACKEND_OPENCL,
        label="OpenCL (Any GPU)",
        description="Any GPU via OpenCL. Broad compatibility but slower than CUDA/DirectML.",
        requires_gpu=True,
    ),
}


@dataclass
class Lc0Options:
    weights_file: str = ""
    backend: str = BACKEND_BLAS
    threads: int = 2
    minibatch_size: int = 256
    nncache_size: int = 20000000
    cpuct: float = 3.4
    temperature: float = 0.0
    temperature_delay: int = 0
    temperature_end: float = 0.0
    softmax_temperature: float = 1.0
    policy_temp: float = 1.4
    max_collision_events: int = 32
    randomize: float = 0.0
    randomness: float = 0.0
    resign_after_moves: int = 3
    resign_score: float = -5.0
    fpu_reduction: str = "0.80"
    cache_history_quality: bool = True
    extra_score_multiplier: float = 0.0

    def to_uci_options(self) -> dict[str, str]:
        opts: dict[str, str] = {}
        if self.weights_file:
            opts["WeightsFile"] = self.weights_file
        if self.backend:
            opts["Backend"] = self.backend
        if self.threads > 1:
            opts["Threads"] = str(self.threads)
        if self.minibatch_size != 256:
            opts["MinibatchSize"] = str(self.minibatch_size)
        if self.nncache_size != 20000000:
            opts["NNCacheSize"] = str(self.nncache_size)
        if self.cpuct != 3.4:
            opts["CPuct"] = str(self.cpuct)
        if self.temperature != 0.0:
            opts["Temperature"] = str(self.temperature)
        if self.temperature_delay != 0:
            opts["TemperatureDelay"] = str(self.temperature_delay)
        if self.temperature_end != 0.0:
            opts["TemperatureEnd"] = str(self.temperature_end)
        if self.softmax_temperature != 1.0:
            opts["SoftmaxTemperature"] = str(self.softmax_temperature)
        if self.policy_temp != 1.4:
            opts["PolicyTemperature"] = str(self.policy_temp)
        if self.max_collision_events != 32:
            opts["MaxCollisionEvents"] = str(self.max_collision_events)
        if self.randomize != 0.0:
            opts["Randomize"] = str(self.randomize)
        if self.randomness != 0.0:
            opts["Randomness"] = str(self.randomness)
        if self.resign_after_moves != 3:
            opts["ResignAfterMoves"] = str(self.resign_after_moves)
        if self.resign_score != -5.0:
            opts["ResignScore"] = str(self.resign_score)
        if self.fpu_reduction != "0.80":
            opts["FPUReduction"] = self.fpu_reduction
        if not self.cache_history_quality:
            opts["CacheHistoryQuality"] = "false"
        if self.extra_score_multiplier != 0.0:
            opts["ExtrascoreMultiplier"] = str(self.extra_score_multiplier)
        return opts


@dataclass(frozen=True)
class NetworkInfo:
    name: str
    url: str
    sha256: str
    size_bytes: int
    description: str
    recommended_for: str = ""
    is_default: bool = False


DEFAULT_NETWORKS: list[NetworkInfo] = [
    NetworkInfo(
        name="T1-256x10-distilled",
        url="https://lczero.org/networks/T1-256x10-distilled.pb.gz",
        sha256="",
        size_bytes=0,
        description="Small distilled network (~30 MB). Best for CPU and mobile.",
        recommended_for="cpu, mobile, android",
        is_default=True,
    ),
    NetworkInfo(
        name="BT4-it332",
        url="https://lczero.org/networks/BT4-it332.pb.gz",
        sha256="",
        size_bytes=0,
        description="Large tournament network (~365 MB). Best for desktop GPU.",
        recommended_for="gpu, desktop",
    ),
    NetworkInfo(
        name="T2-384x10-td4",
        url="https://lczero.org/networks/T2-384x10-td4.pb.gz",
        sha256="",
        size_bytes=0,
        description="Medium network (~100 MB). Good balance for CPU/GPU.",
        recommended_for="cpu, gpu",
    ),
    NetworkInfo(
        name="BT3-it332",
        url="https://lczero.org/networks/BT3-it332.pb.gz",
        sha256="",
        size_bytes=0,
        description="Previous generation tournament network (~350 MB).",
        recommended_for="gpu, desktop",
    ),
]


def get_default_options_for_platform() -> Lc0Options:
    sys_platform = platform.system().lower()
    machine = platform.machine().lower()

    opts = Lc0Options()
    opts.backend = BACKEND_BLAS
    opts.weights_file = ""

    if sys_platform == "android" or "android" in sys_platform:
        opts.threads = 4
        opts.minibatch_size = 64
        opts.nncache_size = 10000000
    elif sys_platform == "darwin":
        opts.threads = 4
        opts.minibatch_size = 128
    elif sys_platform == "windows":
        opts.threads = 2
        opts.minibatch_size = 256
    else:
        opts.threads = 2
        opts.minibatch_size = 256

    return opts


def recommend_backends_for_system() -> list[str]:
    sys_platform = platform.system().lower()

    if sys_platform == "android" or "android" in sys_platform:
        return [BACKEND_BLAS]

    if sys_platform == "darwin":
        return [BACKEND_BLAS]

    recommended = [BACKEND_BLAS]
    if sys_platform == "windows":
        recommended.append(BACKEND_DXIL)

    try:
        import subprocess
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            recommended.append(BACKEND_CUDA)
            recommended.append(BACKEND_CUDNN)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return recommended


LC0_ANDROID_CONFIG = {
    "github_repo": "LeelaChessZero/lc0",
    "asset_name_filter": "android",
    "binary_name": "lc0",
    "archive_binary_name": "liblc0.so",
    "archive_extra_files": {
        "lib/arm64-v8a/libopenblas.so": None,
        "lib/arm64-v8a/libc++_shared.so": None,
        "lib/arm64-v8a/libgfortran.so": None,
    },
}

LC0_WINDOWS_CPU_CONFIG = {
    "github_repo": "LeelaChessZero/lc0",
    "asset_name_filter": "windows-cpu-openblas",
    "binary_name": "lc0.exe",
    "archive_binary_name": "lc0.exe",
    "archive_extra_files": {},
}

LC0_MACOS_CONFIG = {
    "github_repo": "LeelaChessZero/lc0",
    "asset_name_filter": "macos",
    "binary_name": "lc0",
    "archive_binary_name": "lc0",
    "archive_extra_files": {},
}


DEFAULT_LC0_CONFIGS = {
    "android": LC0_ANDROID_CONFIG,
    "windows": LC0_WINDOWS_CPU_CONFIG,
    "macos": LC0_MACOS_CONFIG,
}
