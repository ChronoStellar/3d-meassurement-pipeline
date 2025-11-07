# handler.py
# --------------------------------------------------------------
# RunPod Serverless handler
# --------------------------------------------------------------
# Input  : {"video": <base64-encoded video bytes> }   (or multipart/form-data)
# Output : { "status": "success", "measurements": { … } }
#          or { "status": "error",   "message": "..."}
# --------------------------------------------------------------

import os
import json
import base64
import tempfile
import runpod
from pathlib import Path

# ---- Your pipeline ------------------------------------------------
from main import run_full_pipeline   # <-- the function you already built

# RunPod gives us a temporary directory that is writable
TMP_DIR = Path("/tmp/runpod")
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
def _save_uploaded_video(payload: dict) -> Path:
    """
    Accepts either:
      • {"video": "<base64 string>"}   (RunPod JSON payload)
      • multipart/form-data with key "video"
    Returns a Path to the saved video file.
    """
    video_bytes = None

    # 1. JSON base64 payload (most common for RunPod)
    if "video" in payload and isinstance(payload["video"], str):
        try:
            video_bytes = base64.b64decode(payload["video"])
        except Exception as e:
            raise ValueError(f"Invalid base64 video data: {e}")

    # 2. Fallback for multipart/form-data (if you call via curl -F)
    if video_bytes is None and "files" in payload:
        # RunPod wraps multipart files under "files"
        for fname, fdata in payload["files"].items():
            if fname.lower().endswith(('.mp4', '.mov', '.avi')):
                video_bytes = fdata
                break

    if video_bytes is None:
        raise ValueError("No video data found in request")

    # Save to a unique temp file
    tmp_file = TMP_DIR / f"input_{os.urandom(4).hex()}.mp4"
    tmp_file.write_bytes(video_bytes)
    return tmp_file


# ------------------------------------------------------------------
def handler(job: dict) -> dict:
    """
    RunPod entry-point.
    `job` contains:
        • job["id"]          – request id
        • job["input"]       – user payload
    """
    try:
        input_payload = job.get("input", {})
        video_path = _save_uploaded_video(input_payload)

        # --------------------------------------------------------------
        # Run your full pipeline (video → VIBE → PLY → measurements)
        # --------------------------------------------------------------
        result = run_full_pipeline(str(video_path))

        # Clean-up the temp video ASAP
        try:
            video_path.unlink()
        except Exception:
            pass

        # --------------------------------------------------------------
        # Normalise the output
        # --------------------------------------------------------------
        if result.get("status") == "success":
            # `run_full_pipeline` returns JSON string inside `data`
            measurements = json.loads(result["data"])
            return {
                "status": "success",
                "measurements": measurements
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Unknown pipeline error")
            }

    except Exception as exc:
        # Any unhandled exception → error response
        return {
            "status": "error",
            "message": str(exc)
        }

runpod.serverless.start({'handler': handler})

# ------------------------------------------------------------------
# For local testing (optional)
# ------------------------------------------------------------------
# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) < 2:
#         print("Usage: python handler.py <path-to-video.mp4>")
#         sys.exit(1)

#     result = handler({
#         "input": {
#             "video": base64.b64encode(Path(sys.argv[1]).read_bytes()).decode()
#         }
#     })

#     if result["status"] == "success":
#         print("SUCCESS! Measurements:")
#         for k, v in result["measurements"].items():
#             print(f"  {k}: {v} cm")
#     else:
#         print(f"ERROR: {result['message']}")