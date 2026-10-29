"""Create a local Gemma4 alias with a separate upstream vision projector.

Ollama's unified E4B projector has a Windows compatibility bug (#16532).
This reuses the installed language-model blob and downloads only the matching
ggml-org projector. It does not change the original model or any chat data.
Run with the app's Python environment while the local Ollama server is running.
"""
from __future__ import annotations

import hashlib
from io import BytesIO
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re
import shutil
import time

import httpx
from PIL import Image, ImageDraw, ImageFont

BASE_MODEL = "gemma4:e4b"
VISION_MODEL = "gemma4-project-vision:e4b"
PROJECTOR_SHA256 = "197f49a93027f9843772bd24a6a9e0be2a32a788de5a3def330e9c585d86edd1"
PROJECTOR_SIZE = 559874816
PROJECTOR_URL = (
    "https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF/resolve/"
    "b8093469224f83f5c38f691eb906c380e9e63114/mmproj-gemma-4-E4B-it-Q8_0.gguf"
)


def download_projector(destination: Path) -> None:
    partial = destination.with_suffix(".partial")
    start = partial.stat().st_size if partial.exists() else 0
    if start > PROJECTOR_SIZE:
        raise RuntimeError("The partial projector file has an unexpected size.")
    block_size = 8 * 1024 * 1024
    blocks = [(offset, min(offset + block_size, PROJECTOR_SIZE) - 1)
              for offset in range(start, PROJECTOR_SIZE, block_size)]
    print(f"Resuming projector at {start // 1048576} / {PROJECTOR_SIZE // 1048576} MiB.", flush=True)

    def fetch(block: tuple[int, int]) -> tuple[Path, int]:
        first, last = block
        part = destination.with_suffix(f".part-{first}")
        size = last - first + 1
        if part.exists() and part.stat().st_size == size:
            return part, size
        for attempt in range(3):
            try:
                with httpx.stream("GET", PROJECTOR_URL, follow_redirects=True, timeout=60,
                                  headers={"Range": f"bytes={first}-{last}"}) as response:
                    response.raise_for_status()
                    expected = f"bytes {first}-{last}/{PROJECTOR_SIZE}"
                    if response.status_code != 206 or response.headers.get("content-range") != expected:
                        raise RuntimeError("The server did not return the requested projector range.")
                    with part.open("wb") as target:
                        for chunk in response.iter_bytes(1024 * 1024):
                            target.write(chunk)
                if part.stat().st_size != size:
                    raise RuntimeError("Incomplete projector download range.")
                return part, size
            except (httpx.HTTPError, RuntimeError):
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
        raise RuntimeError("Could not download projector range.")

    completed = start
    with ThreadPoolExecutor(max_workers=8) as pool:
        for future in as_completed([pool.submit(fetch, block) for block in blocks]):
            _, size = future.result()
            completed += size
            print(f"Downloaded {completed // 1048576} / {PROJECTOR_SIZE // 1048576} MiB.", flush=True)
    with partial.open("ab") as target:
        for first, _ in blocks:
            part = destination.with_suffix(f".part-{first}")
            with part.open("rb") as source:
                shutil.copyfileobj(source, target)
    for first, _ in blocks:
        destination.with_suffix(f".part-{first}").unlink()
    partial.replace(destination)


def main() -> None:
    cache = Path(__file__).resolve().parents[1] / "backend" / "logs" / "local_deploy"
    cache.mkdir(parents=True, exist_ok=True)
    downloaded = cache / "gemma4-vision-projector.gguf"
    with httpx.Client(base_url="http://127.0.0.1:11434", timeout=300) as ollama:
        shown = ollama.post("/api/show", json={"model": BASE_MODEL})
        shown.raise_for_status()
        base = shown.json()
        match = re.search(r"^FROM .*sha256[-:]([a-f0-9]{64})\s*$", base.get("modelfile", ""), re.MULTILINE)
        if not match:
            raise RuntimeError("Could not identify the installed Gemma4 model blob.")
        base_digest = "sha256:" + match.group(1)
        digest = "sha256:" + PROJECTOR_SHA256
        blob = ollama.head("/api/blobs/" + digest)
        if blob.status_code != 200:
            if blob.status_code != 404:
                blob.raise_for_status()
            if not downloaded.exists():
                download_projector(downloaded)
            with downloaded.open("rb") as source:
                actual_hash = hashlib.file_digest(source, "sha256").hexdigest()
            if actual_hash != PROJECTOR_SHA256:
                raise RuntimeError("Projector checksum mismatch; nothing was imported.")
            print("Projector checksum verified. Importing into local Ollama.", flush=True)
            with downloaded.open("rb") as source:
                uploaded = ollama.post("/api/blobs/" + digest, content=iter(lambda: source.read(1024 * 1024), b""),
                    headers={"Content-Length": str(downloaded.stat().st_size)})
            uploaded.raise_for_status()
            # Ollama now holds its own copy of the projector.
            downloaded.unlink()
        # This alias is dedicated to this repair; leave the original tag intact.
        payload = {
            "model": VISION_MODEL,
            "files": {"gemma4-e4b.gguf": base_digest, "mmproj.gguf": digest},
            "renderer": "gemma4", "parser": "gemma4",
            "parameters": {"temperature": 1, "top_k": 64, "top_p": 0.95},
            "license": base.get("license", ""),
        }
        with ollama.stream("POST", "/api/create", json=payload) as response:
            response.raise_for_status()
            completed = False
            for line in response.iter_lines():
                if not line:
                    continue
                status = json.loads(line)
                if status.get("error"):
                    raise RuntimeError(status["error"])
                if status.get("status"):
                    print(status["status"], flush=True)
                completed = status.get("status") == "success"
            if not completed:
                raise RuntimeError("Model creation did not report success.")
        print(f"Created {VISION_MODEL}; the original {BASE_MODEL} is preserved.", flush=True)
        verify_vision(ollama, cache)


def verify_vision(ollama: httpx.Client, cache: Path) -> None:
    import base64

    picture = Image.new("RGB", (480, 280), "white")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 160)
    except OSError:
        font = ImageFont.load_default(size=160)
    ImageDraw.Draw(picture).text((240, 140), "17", fill="black", font=font, anchor="mm")
    encoded = BytesIO()
    picture.save(encoded, format="JPEG", quality=92)
    response = ollama.post("/api/chat", json={
        "model": VISION_MODEL, "stream": False, "think": False,
        "messages": [{"role": "user", "content": "Read the number printed in this image. Reply with that number only.",
                      "images": [base64.b64encode(encoded.getvalue()).decode("ascii")]}],
        "options": {"temperature": 0, "num_predict": 64},
    }, timeout=900)  # The first load of the 10 GB model can be slow on CPU-only PCs.
    response.raise_for_status()
    answer = response.json().get("message", {}).get("content", "").strip()
    if answer.strip("*` .\n") != "17":
        raise RuntimeError(f"The repaired model did not pass the image check: {answer}")
    print("Vision check passed: the model read the number from the image correctly.", flush=True)
    # The launcher prefers this alias only after the actual image check passes.
    (cache / "vision-model.json").write_text(json.dumps({
        "model": VISION_MODEL, "base_model": BASE_MODEL,
        "projector_sha256": PROJECTOR_SHA256, "vision_verified": True,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
