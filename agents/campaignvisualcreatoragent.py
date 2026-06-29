# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import base64
import os
import requests as _requests
from typing import TypedDict
from dotenv import load_dotenv
from agents.llm_factory import get_llm
from agents.security import sanitize_input, wrap_user_content, build_safe_system_message
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

_NON_VISION_MODELS = {"gpt-3.5-turbo", "deepseek-chat"}


class CreatorState(TypedDict):
    campaign_title: str
    campaign_content: str
    campaign_segment: str
    campaign_date: str
    visual_description: str
    campaign_criteria: str
    example_image_bytes: bytes | None
    example_image_mime: str | None
    selected_model: str
    dalle_prompt: str
    generated_image_url: str
    generated_image_bytes: bytes | None
    error: str | None


def build_prompt_node(state: CreatorState):
    from user.prompt_store import get_prompt

    model = state.get("selected_model", "claude-sonnet-4-6")
    llm = get_llm(model)

    title, _ = sanitize_input(state.get("campaign_title", ""))
    content, _ = sanitize_input(state.get("campaign_content", ""))
    segment, _ = sanitize_input(state.get("campaign_segment", ""))
    date_str = state.get("campaign_date", "")
    visual_desc, _ = sanitize_input(state.get("visual_description", ""))
    criteria, _ = sanitize_input(state.get("campaign_criteria", ""))

    has_example = (
        state.get("example_image_bytes") is not None
        and model not in _NON_VISION_MODELS
    )
    example_note = (
        "Ek olarak bir örnek görsel sağlanmıştır. Bu görselin stilini ve düzenini referans al."
        if has_example
        else ""
    )

    template = get_prompt("visual_creator_prompt", "prompts/visual_creator_prompt.txt")
    prompt_text = template.format(
        title=title,
        content=content,
        segment=segment,
        date=date_str,
        visual_description=visual_desc,
        criteria=criteria,
        example_note=example_note,
    )

    if has_example:
        b64 = base64.b64encode(state["example_image_bytes"]).decode("utf-8")
        mime = state.get("example_image_mime", "image/jpeg")
        human_msg = HumanMessage(content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ])
    else:
        human_msg = HumanMessage(content=prompt_text)

    messages = [
        SystemMessage(content=build_safe_system_message()),
        human_msg,
    ]

    response = llm.invoke(messages)
    dalle_prompt = response.content.strip()

    # DALL-E 3 has a 4000 character limit for prompts
    if len(dalle_prompt) > 3900:
        dalle_prompt = dalle_prompt[:3900]

    return {"dalle_prompt": dalle_prompt, "error": None}


def generate_image_node(state: CreatorState):
    dalle_prompt = state.get("dalle_prompt", "")
    if not dalle_prompt:
        return {"error": "Görsel prompt oluşturulamadı.", "generated_image_bytes": None}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        img_response = _requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        return {
            "generated_image_url": image_url,
            "generated_image_bytes": img_response.content,
            "error": None,
        }
    except Exception as e:
        return {
            "generated_image_bytes": None,
            "error": str(e),
        }


workflow = StateGraph(CreatorState)
workflow.add_node("build_prompt", build_prompt_node)
workflow.add_node("generate_image", generate_image_node)
workflow.set_entry_point("build_prompt")
workflow.add_edge("build_prompt", "generate_image")
workflow.add_edge("generate_image", END)

app = workflow.compile()
