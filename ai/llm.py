import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings
logger = logging.getLogger(__name__)

class LLMClient:

    def __init__(self) -> None:
        self._provider = settings.llm.provider.lower()
        self._client = self._build_client()
        logger.info(f"[LLM] Provedor ativo: {self._provider} | Modelo: {self.model_name}")

    def _build_client(self):
        if self._provider == "groq":
            return self._build_groq()
        elif self._provider == "gemini":
            return self._build_gemini()
        else:
            raise ValueError(
                f"[LLM] Provedor desconhecido: '{self._provider}'. "
                "Use 'groq' ou 'gemini' no LLM_PROVIDER do .env."
            )

    def _build_groq(self):
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "[LLM] Pacote 'groq' não instalado.\n"
                "  → Execute: pip install groq"
            )

        api_key = settings.llm.groq_api_key
        if not api_key:
            raise EnvironmentError(
                "[LLM] GROQ_API_KEY não encontrada no .env.\n"
                "  → Obtenha sua chave em: https://console.groq.com/keys"
            )

        self.model_name = settings.llm.groq_model
        from groq import Groq
        return Groq(api_key=api_key)

    def _build_gemini(self):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "[LLM] Pacote 'google-generativeai' não instalado.\n"
                "  → Execute: pip install google-generativeai"
            )

        api_key = settings.llm.gemini_api_key
        if not api_key:
            raise EnvironmentError(
                "[LLM] GEMINI_API_KEY não encontrada no .env.\n"
                "  → Obtenha sua chave em: https://aistudio.google.com/app/apikey"
            )

        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model_name = settings.llm.gemini_model
        return genai.GenerativeModel(self.model_name)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
    ) -> str:
        if self._provider == "groq":
            return self._generate_groq(prompt, temperature, max_tokens, system_prompt)
        elif self._provider == "gemini":
            return self._generate_gemini(prompt, temperature, max_tokens, system_prompt)
        else:
            raise RuntimeError(f"[LLM] Provedor não suportado: {self._provider}")

    def generate_json(
        self,
        prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Gera resposta e parseia como JSON, removendo blocos markdown se presentes."""
        raw = self.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"[LLM] Resposta não é JSON válido: {e}\n---\n{cleaned[:300]}\n---")
            raise ValueError(f"[LLM] Resposta inválida do modelo: {e}")

    def _generate_groq(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str],
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[LLM] Erro na chamada ao Groq: {e}")
            raise RuntimeError(f"[LLM] Groq falhou: {e}") from e

    def _generate_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str],
    ) -> str:
        import google.generativeai as genai

        # Gemini não suporta system prompt separado — concatena ao prompt
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            response = self._client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"[LLM] Erro na chamada ao Gemini: {e}")
            raise RuntimeError(f"[LLM] Gemini falhou: {e}") from e

_llm_instance: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance

def llm_generate(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    system_prompt: Optional[str] = None,
) -> str:
    return get_llm_client().generate(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
    )

def llm_generate_json(
    prompt: str,
    temperature: float = 0.4,
    max_tokens: int = 1024,
    system_prompt: Optional[str] = None,
) -> dict:
    return get_llm_client().generate_json(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
    )
