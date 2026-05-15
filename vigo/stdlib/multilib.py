"""ViGo Standard Library: Multimedia (multilib)
Provides image processing, audio handling, and basic video utilities.
Uses Pillow for images, wave/struct for audio (stdlib).
"""
import os
import io
import struct
import wave
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register all multilib functions into the given ViGo environment."""

    # ── Image operations (Pillow) ──

    def _require_pil():
        try:
            from PIL import Image, ImageFilter, ImageEnhance
            return (Image, ImageFilter, ImageEnhance)
        except ImportError:
            raise ViGoError("Pillow not installed. Run: pip install Pillow")

    def img_open(filepath):
        Image, _, _ = _require_pil()
        img = Image.open(filepath)
        return {"_pil_image": img, "width": img.width, "height": img.height,
                "format": img.format, "mode": img.mode}

    def img_save(img_obj, filepath, format=None):
        pil_img = img_obj.get("_pil_image")
        if not pil_img:
            raise ViGoError("Invalid image object")
        pil_img.save(filepath, format=format)
        return True

    def img_resize(img_obj, width, height):
        pil_img = img_obj.get("_pil_image")
        if not pil_img:
            raise ViGoError("Invalid image object")
        Image, _, _ = _require_pil()
        resized = pil_img.resize((int(width), int(height)), Image.LANCZOS)
        return {"_pil_image": resized, "width": resized.width, "height": resized.height,
                "format": pil_img.format, "mode": pil_img.mode}

    def img_thumbnail(img_obj, max_size):
        pil_img = img_obj.get("_pil_image")
        if not pil_img:
            raise ViGoError("Invalid image object")
        thumb = pil_img.copy()
        thumb.thumbnail((int(max_size), int(max_size)))
        return {"_pil_image": thumb, "width": thumb.width, "height": thumb.height,
                "format": pil_img.format, "mode": pil_img.mode}

    def img_crop(img_obj, left, top, right, bottom):
        pil_img = img_obj.get("_pil_image")
        if not pil_img:
            raise ViGoError("Invalid image object")
        cropped = pil_img.crop((int(left), int(top), int(right), int(bottom)))
        return {"_pil_image": cropped, "width": cropped.width, "height": cropped.height,
                "format": pil_img.format, "mode": pil_img.mode}

    def img_rotate(img_obj, degrees):
        pil_img = img_obj.get("_pil_image")
        if not pil_img:
            raise ViGoError("Invalid image object")
        rotated = pil_img.rotate(float(degrees), expand=True)
        return {"_pil_image": rotated, "width": rotated.width, "height": rotated.height,
                "format": pil_img.format, "mode": pil_img.mode}

    def img_blur(img_obj, radius=2):
        pil_img = img_obj.get("_pil_image")
        if not pil_img:
            raise ViGoError("Invalid image object")
        _, ImageFilter, _ = _require_pil()
        blurred = pil_img.filter(ImageFilter.GaussianBlur(float(radius)))
        return {"_pil_image": blurred, "width": blurred.width, "height": blurred.height,
                "format": pil_img.format, "mode": pil_img.mode}

    def img_grayscale(img_obj):
        pil_img = img_obj.get("_pil_image")
        if not pil_img:
            raise ViGoError("Invalid image object")
        gray = pil_img.convert("L")
        return {"_pil_image": gray, "width": gray.width, "height": gray.height,
                "format": pil_img.format, "mode": gray.mode}

    def img_info(filepath):
        Image, _, _ = _require_pil()
        img = Image.open(filepath)
        return {"width": img.width, "height": img.height, "format": img.format,
                "mode": img.mode, "filepath": filepath}

    # ── Audio operations (stdlib wave) ──

    def audio_info(filepath):
        try:
            wf = wave.open(filepath, 'rb')
            info = {
                "channels": wf.getnchannels(),
                "sample_width": wf.getsampwidth(),
                "framerate": wf.getframerate(),
                "frames": wf.getnframes(),
                "duration": wf.getnframes() / max(wf.getframerate(), 1),
                "filepath": filepath,
            }
            wf.close()
            return info
        except wave.Error:
            raise ViGoError(f"Not a valid WAV file: {filepath}")

    def audio_read_samples(filepath, max_samples=1000):
        try:
            wf = wave.open(filepath, 'rb')
            frames = wf.readframes(min(int(max_samples), wf.getnframes()))
            wf.close()
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            fmt = {1: 'b', 2: 'h', 4: 'i'}.get(sample_width, 'h')
            samples = struct.unpack(f'<{len(frames) // sample_width}{fmt}', frames)
            if channels == 1:
                return list(samples)
            return [list(samples[i:i+channels]) for i in range(0, len(samples), channels)]
        except wave.Error:
            raise ViGoError(f"Not a valid WAV file: {filepath}")

    def audio_create_silence(filepath, duration_sec, framerate=44100, channels=1, sample_width=2):
        try:
            wf = wave.open(filepath, 'wb')
            wf.setnchannels(int(channels))
            wf.setsampwidth(int(sample_width))
            wf.setframerate(int(framerate))
            nframes = int(duration_sec * int(framerate))
            wf.writeframes(b'\x00' * nframes * int(sample_width))
            wf.close()
            return True
        except Exception as e:
            raise ViGoError(f"Failed to create audio file: {e}")

    # ── Video utilities (basic info via subprocess ffprobe) ──

    def video_info(filepath):
        try:
            import subprocess
            import json
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filepath],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            raise ViGoError("ffprobe failed")
        except FileNotFoundError:
            raise ViGoError("ffprobe not found. Install ffmpeg: https://ffmpeg.org")
        except Exception as e:
            raise ViGoError(f"Video info error: {e}")

    def video_extract_audio(video_path, audio_path):
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-y", audio_path],
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise ViGoError("ffmpeg not found. Install ffmpeg: https://ffmpeg.org")

    # ── Registration ──

    env.define("img_open", BuiltinFunction(img_open, "img_open"))
    env.define("img_save", BuiltinFunction(img_save, "img_save"))
    env.define("img_resize", BuiltinFunction(img_resize, "img_resize"))
    env.define("img_thumbnail", BuiltinFunction(img_thumbnail, "img_thumbnail"))
    env.define("img_crop", BuiltinFunction(img_crop, "img_crop"))
    env.define("img_rotate", BuiltinFunction(img_rotate, "img_rotate"))
    env.define("img_blur", BuiltinFunction(img_blur, "img_blur"))
    env.define("img_grayscale", BuiltinFunction(img_grayscale, "img_grayscale"))
    env.define("img_info", BuiltinFunction(img_info, "img_info"))
    env.define("audio_info", BuiltinFunction(audio_info, "audio_info"))
    env.define("audio_read_samples", BuiltinFunction(audio_read_samples, "audio_read_samples"))
    env.define("audio_create_silence", BuiltinFunction(audio_create_silence, "audio_create_silence"))
    env.define("video_info", BuiltinFunction(video_info, "video_info"))
    env.define("video_extract_audio", BuiltinFunction(video_extract_audio, "video_extract_audio"))