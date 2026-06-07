# -*- coding: utf-8 -*-
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

@lru_cache(maxsize=16)
def get_llm(model: str, temperature: float = 0):
    if model.startswith("gpt-"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=temperature)
    elif model.startswith("claude-"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model)
    elif model.startswith("gemini-"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )
    elif model.startswith("deepseek-"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url="https://api.deepseek.com",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=temperature)
