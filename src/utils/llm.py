"""Groq LLMs module for LangChain integration."""

from typing import Optional

from langchain_groq import ChatGroq

from ..config.logging import Logger
from ..config.settings import get_settings
from ..config.singleton import Singleton


class GroqLLM(metaclass=Singleton):
    """A class to interact with Groq LLMs using the LangChain interface."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        streaming: bool = False,
        max_tokens: int = None,
    ):
        """
        Initialize the GroqLLM class.
        Args:
            model_name (str): The name of the Groq model to use. Default is "meta-llama/llama-4-maverick-17b-128e-instruct".
        """
        self.settings = get_settings()
        self.logger = Logger().get_logger(self.__class__.__name__)

        self.model = model or self.settings.DEFAULT_MODEL
        self.temperature = temperature or self.settings.DEFAULT_TEMPERATURE
        self.streaming = streaming
        self.max_tokens = max_tokens

    def get_llm(self):
        """Get the Groq LLM instance."""
        self.logger.debug(f"Initializing Groq LLM with model: {self.model}")

        return ChatGroq(
            model=self.model,
            temperature=self.temperature,
            streaming=self.streaming,
            max_tokens=self.max_tokens,
        )


# Example usage (for testing purposes)
if __name__ == "__main__":
    groq_llm = GroqLLM()
    llm_instance = groq_llm.get_llm()
    print(f"LLM instance: {llm_instance}")
    print("================================================")
    print(llm_instance.invoke("What is the capital of Germany?").content)
    print("================================================")