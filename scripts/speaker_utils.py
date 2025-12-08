"""Shared helpers for speaker embedding and assignment workflows."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import yaml
from python_speech_features import mfcc
import torch

AUDIO_DIR = Path("data/audio/all_in")
TRANSCRIPTION_DIRS = {
    "assemblyai": Path("data/processed/transcripts_assemblyai"),
    "deepgram": Path("data/processed/transcripts_deepgram"),
    "openai": Path("data/processed/transcripts_openai"),
    "speechmatics": Path("data/processed/transcripts_speechmatics"),
}
TRANSCRIPTS_DIR = TRANSCRIPTION_DIRS["speechmatics"]
CURRENT_TRANSCRIPTION_SOURCE = "speechmatics"
SPEAKER_DIR = Path("data/speakers")
CONFIG_PATH = Path("config/speakers.yaml")
_SPEECHBRAIN_MODEL = None


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "ffmpeg is required but not found on PATH. Install ffmpeg and retry."
        )


def load_segments(episode_id: str) -> List[Dict[str, float]]:
    segments_path = TRANSCRIPTS_DIR / episode_id / "segments.json"
    if not segments_path.exists():
        raise SystemExit(
            f"Segments file not found: {segments_path} "
            f"(source={CURRENT_TRANSCRIPTION_SOURCE}). Transcribe the episode first."
        )
    return json.loads(segments_path.read_text())


def load_audio_segment(
    audio_path: Path, start: float, end: float, sample_rate: int = 16000
) -> np.ndarray:
    duration = max(end - start, 0.5)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(start, 0):.3f}",
        "-i",
        str(audio_path),
        "-t",
        f"{duration:.3f}",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    data = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32)
    if data.size == 0:
        return np.array([], dtype=np.float32)
    return data / 32768.0


def compute_embedding(
    waveform: np.ndarray, sample_rate: int = 16000, *, strategy: str = "mfcc"
) -> Optional[np.ndarray]:
    strategy = strategy.lower()
    if strategy not in {"mfcc", "speechbrain"}:
        raise SystemExit(f"Unknown embedding strategy: {strategy}")
    if waveform.size == 0:
        return None

    if strategy == "mfcc":
        feats = mfcc(waveform, samplerate=sample_rate, numcep=20, nfilt=26, nfft=2048)
        if feats.size == 0:
            return None
        mean = feats.mean(axis=0)
        std = feats.std(axis=0)
        return np.concatenate([mean, std])

    recognizer = get_speechbrain_recognizer()
    tensor = torch.tensor(waveform, dtype=torch.float32)
    # reshape to [batch, time]
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    embeddings = recognizer.encode_batch(tensor, normalize=True)
    if embeddings.ndim > 2:
        embeddings = embeddings.squeeze()
    return embeddings.detach().cpu().numpy().flatten()


def aggregate_embeddings(vectors: List[np.ndarray]) -> np.ndarray:
    stacked = np.stack(vectors, axis=0)
    return stacked.mean(axis=0)


def select_segments(
    segments: List[Dict[str, float]],
    label: str,
    *,
    min_duration: float,
    max_segments: int,
) -> List[Tuple[float, float]]:
    matches = [seg for seg in segments if seg.get("speaker_label") == label]

    def duration(seg: Dict[str, float]) -> float:
        start = float(seg.get("start") or 0.0)
        end = float(seg.get("end") or start)
        return max(end - start, 0.0)

    sorted_segments = sorted(matches, key=duration, reverse=True)
    selected: List[Tuple[float, float]] = []
    for seg in sorted_segments:
        start = float(seg.get("start") or 0.0)
        end = float(seg.get("end") or start)
        if (end - start) < min_duration:
            continue
        selected.append((start, end))
        if len(selected) >= max_segments:
            break
    return selected


def load_config(path: Path = CONFIG_PATH) -> Dict[str, dict]:
    if not path.exists():
        raise SystemExit(f"Speaker config not found at {path}")
    data = yaml.safe_load(path.read_text()) or {}
    data.setdefault("speakers", {})
    return data


def save_config(data: Dict[str, dict], path: Path = CONFIG_PATH) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def update_embedding_entry(
    config: Dict[str, dict], speaker_key: str, embedding_path: Path, *, strategy: str
) -> None:
    speakers = config.setdefault("speakers", {})
    info = speakers.get(speaker_key)
    if info is None:
        info = {"display_name": speaker_key, "role": "guest"}
        speakers[speaker_key] = info
    info["embedding"] = str(embedding_path)
    info["embedding_strategy"] = strategy


def set_transcripts_dir(source: str) -> Path:
    """Set the active transcripts directory based on transcription provider."""
    global TRANSCRIPTS_DIR, CURRENT_TRANSCRIPTION_SOURCE
    normalized = source.lower()
    if normalized not in TRANSCRIPTION_DIRS:
        valid = ", ".join(sorted(TRANSCRIPTION_DIRS))
        raise SystemExit(
            f"Unknown transcription source '{source}'. Choose from: {valid}"
        )
    TRANSCRIPTS_DIR = TRANSCRIPTION_DIRS[normalized]
    CURRENT_TRANSCRIPTION_SOURCE = normalized
    return TRANSCRIPTS_DIR


def get_transcripts_dir() -> Path:
    return TRANSCRIPTS_DIR


def get_speechbrain_recognizer():
    """Lazily load SpeechBrain speaker recognition model."""
    global _SPEECHBRAIN_MODEL
    if _SPEECHBRAIN_MODEL is not None:
        return _SPEECHBRAIN_MODEL

    try:
        import torchaudio  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise SystemExit("speechbrain strategy requires torchaudio installed") from exc

    if not hasattr(torchaudio, "list_audio_backends"):
        torchaudio.list_audio_backends = lambda: []  # type: ignore[assignment]

    try:
        import huggingface_hub  # noqa: WPS433
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            f"speechbrain strategy requires huggingface_hub: {exc}"
        ) from exc

    # Patch API compatibility for speechbrain <-> huggingface_hub token argument
    if not hasattr(huggingface_hub.hf_hub_download, "__patched_speechbrain__"):
        _orig_hf_hub_download = huggingface_hub.hf_hub_download

        def _patched_hf_hub_download(*args, **kwargs):
            if "use_auth_token" in kwargs and "token" not in kwargs:
                kwargs["token"] = kwargs.pop("use_auth_token")
            return _orig_hf_hub_download(*args, **kwargs)

        _patched_hf_hub_download.__patched_speechbrain__ = True  # type: ignore[attr-defined]
        huggingface_hub.hf_hub_download = _patched_hf_hub_download  # type: ignore[assignment]

    try:
        from speechbrain.inference.speaker import SpeakerRecognition  # noqa: WPS433
    except Exception as exc:  # pragma: no cover - model import guard
        raise SystemExit(f"Failed to import SpeechBrain: {exc}") from exc

    try:
        _SPEECHBRAIN_MODEL = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
        )
    except Exception as exc:  # pragma: no cover - download/initialization guard
        raise SystemExit(
            f"Failed to load SpeechBrain model (check network access): {exc}"
        ) from exc
    return _SPEECHBRAIN_MODEL
