"""Pembungkus Gemini API (free tier). Semua pemanggilan model lewat satu tempat ini."""
import time


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        from google import genai
        self._genai = genai
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.jumlah_panggilan = 0
        self.token_input = 0
        self.token_output = 0

    def generate_json(self, system: str, prompt: str, maks_coba: int = 4) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(system_instruction=system, temperature=0.0,
                                          response_mime_type="application/json", max_output_tokens=4096)
        for i in range(maks_coba):
            try:
                r = self.client.models.generate_content(model=self.model, contents=prompt, config=cfg)
                self.jumlah_panggilan += 1
                u = getattr(r, "usage_metadata", None)
                if u:
                    self.token_input += getattr(u, "prompt_token_count", 0) or 0
                    self.token_output += getattr(u, "candidates_token_count", 0) or 0
                return r.text or ""
            except Exception as e:  # kuota free tier: tunggu lalu coba lagi
                pesan = str(e)
                if ("429" in pesan or "RESOURCE_EXHAUSTED" in pesan or "503" in pesan) and i < maks_coba - 1:
                    time.sleep(15 * (i + 1))
                    continue
                raise

    def uji_koneksi(self) -> str:
        r = self.client.models.generate_content(model=self.model, contents="Balas satu kata: siap")
        return (r.text or "").strip()

    def statistik(self) -> dict:
        return {"model": self.model, "jumlah_panggilan_llm": self.jumlah_panggilan,
                "token_input": self.token_input, "token_output": self.token_output}
