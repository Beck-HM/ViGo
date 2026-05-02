"""ViGo Image Generation Library - Stable Diffusion"""
import json
import urllib.request
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class ImageGenerator:
    def __init__(self):
        self.default_host = "http://localhost:7860"  # Automatic1111 WebUI API

    def generate(self, prompt, negative="", steps=20, width=512, height=512, host=None):
        """Generate image via Stable Diffusion WebUI API"""
        url = f"{host or self.default_host}/sdapi/v1/txt2img"
        data = json.dumps({
            "prompt": prompt,
            "negative_prompt": negative,
            "steps": steps,
            "width": width,
            "height": height,
        }).encode('utf-8')

        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                # Save first image
                import base64
                img_data = base64.b64decode(result["images"][0])
                filename = f"vigo_gen_{abs(hash(prompt)) % 100000}.png"
                with open(filename, "wb") as f:
                    f.write(img_data)
                return f"Image saved: {filename}"
        except Exception as e:
            raise ViGoError(f"Image generation failed: {e}. Is Stable Diffusion WebUI running?")


_img_gen = ImageGenerator()


def register(env):
    env.define('img_generate', BuiltinFunction(
        lambda prompt, neg="", steps=20, w=512, h=512, host=None:
            _img_gen.generate(prompt, neg, steps, w, h, host),
        'img_generate'
    ))