# src/content/page_generator.py
"""
Expert Page Generator (REWRITTEN).
Architected for Zero-AI-Footprint content.
Uses Brand DNA Synthesis for fallback and Chain-of-Thought for LLM generation.
"""

import json
import re
import random
import time
import hashlib
from datetime import datetime
from src.utils.logger import logger

def generate_page(brief, llm_config, existing_pages=None, site_wide_faqs=None) -> dict:
    """
    Expert content synthesis pipeline with Autonomous Fallback Chain.
    Uses centralized LLM resolver for cascading key fallback.
    """
    from src.utils.llm_resolver import call_llm_with_fallback
    
    existing_pages = existing_pages or []
    site_wide_faqs = site_wide_faqs or []

    prompt = _build_expert_prompt(brief, existing_pages, site_wide_faqs)
    
    try:
        logger.info(f"FidelityEngine: Generating page for '{brief.target_keyword}' via cascading fallback...")
        raw = call_llm_with_fallback(prompt, llm_config)
        
        if raw:
            json_schema_dict = _extract_json_from_llm(raw)
            if json_schema_dict:
                # Validate the generated content quality
                json_schema_dict = _validate_generated_content(json_schema_dict, brief)
                provider = llm_config.get("provider", "unknown")
                logger.info(f"FidelityEngine: Content generated successfully for '{brief.target_keyword}'")
                return _finalize_result(brief, json_schema_dict, provider)
        
        logger.warning(f"FidelityEngine: LLM returned invalid structure for '{brief.target_keyword}'. Using DNA synthesis.")
    except Exception as e:
        logger.warning(f"FidelityEngine: All providers failed for '{brief.target_keyword}': {e}. Using DNA synthesis.")

    # Site-DNA Synthesis Fallback (Final Safety Net)
    logger.info(f"FidelityEngine: Synthesizing {brief.target_keyword} from Site DNA.")
    json_schema_dict = _synthesize_from_site_dna(brief, existing_pages)
    return _finalize_result(brief, json_schema_dict, "dna_synthesis")

def _finalize_result(brief, schema, method):
    """Final package for the UI/Deployment."""
    return {
        "slug": brief.url_slug,
        "meta_title": schema.get("meta", {}).get("title", brief.page_title),
        "meta_description": schema.get("meta", {}).get("description", brief.meta_description),
        "schema_data": schema,
        "word_count": schema.get("content_metadata", {}).get("word_count", 0),
        "generation_method": method,
    }

def _validate_generated_content(schema: dict, brief) -> dict:
    """
    Quality gate for LLM-generated content.
    Strips AI tropes, ensures minimum section depth, validates structure.
    """
    # Strip AI tropes from all text fields
    ai_tropes = ["unlock", "transform", "navigate", "delve", "landscape",
                 "empower", "game-changer", "cutting-edge", "in conclusion",
                 "look no further", "state-of-the-art", "in today's world"]
    
    def clean_text(text):
        if not isinstance(text, str):
            return text
        for trope in ai_tropes:
            text = re.sub(rf'\b{re.escape(trope)}\b', '', text, flags=re.IGNORECASE)
        # Clean up double spaces
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text
    
    # Clean hero
    hero = schema.get("hero", {})
    hero["headline"] = clean_text(hero.get("headline", ""))
    hero["subheadline"] = clean_text(hero.get("subheadline", ""))
    
    # Clean sections
    for sec in schema.get("sections", []):
        sec["heading"] = clean_text(sec.get("heading", ""))
        sec["body_paragraphs"] = [clean_text(p) for p in sec.get("body_paragraphs", [])]
        if sec.get("callout"):
            sec["callout"]["text"] = clean_text(sec["callout"].get("text", ""))
    
    # Clean FAQs
    for faq in schema.get("faq", []):
        faq["question"] = clean_text(faq.get("question", ""))
        faq["answer"] = clean_text(faq.get("answer", ""))
    
    # Validate minimum section count
    if len(schema.get("sections", [])) < 2:
        # Add a supplemental section
        kw = brief.target_keyword
        niche = brief.niche or "our field"
        schema.setdefault("sections", []).append({
            "id": "practical-application",
            "type": "body",
            "heading": f"Practical Application of {kw.title()}",
            "body_paragraphs": [
                f"Implementing {kw} effectively requires a structured approach that accounts for the specific demands of the {niche} sector. Our methodology begins with a thorough assessment of current capabilities and gaps.",
                f"By grounding {kw} in measurable outcomes rather than theoretical frameworks, we ensure that every implementation delivers tangible value to stakeholders."
            ]
        })
    
    # Validate FAQ quality
    valid_faqs = []
    for faq in schema.get("faq", []):
        q, a = faq.get("question", ""), faq.get("answer", "")
        if len(q) > 15 and len(a) > 40:
            valid_faqs.append(faq)
    schema["faq"] = valid_faqs
    
    return schema


def _synthesize_from_site_dna(brief, existing_pages: list) -> dict:
    """
    Constructs a page using actual Site DNA fragments.
    v2: Produces richer content with 4+ sections, multiple FAQs,
    and service-specific detail.
    """
    kw = brief.target_keyword
    niche = brief.niche
    mission = (brief.site_profile_md or f"Expert authority in {niche}.").split("\n")[0].replace("# ", "")
    services = brief.services or [niche]
    pain_points = brief.pain_points or []
    brand = mission.split(":")[-1].strip() if ":" in mission else "Our industry experts"
    
    # Format services for display
    svc_names = []
    for s in services[:4]:
        if isinstance(s, dict):
            svc_names.append(s.get("name", str(s)))
        else:
            svc_names.append(str(s))
    
    svc_text = ", ".join(svc_names[:3]) if svc_names else niche
    
    # Hero
    hero = {
        "headline": f"{kw.title()}: A Practitioner's Perspective on {niche}",
        "subheadline": f"How {brand} applies {kw} methodology to deliver measurable results in {niche}.",
        "cta_text": f"Discuss Your {kw.title()} Needs"
    }
    
    # Build rich sections
    sections = []
    
    # Section 1: Strategic Overview
    sections.append({
        "id": "strategic-overview", "type": "body",
        "heading": f"Understanding {kw.title()} in the Context of {niche}",
        "body_paragraphs": [
            f"In {niche}, {kw} is not an isolated concern — it intersects directly with core operational requirements including {svc_text}. {brand}'s approach treats {kw} as a systemic capability rather than a point solution.",
            f"Our fieldwork across multiple {niche} engagements has revealed that organizations which integrate {kw} into their foundational processes see measurably better outcomes than those who treat it as an afterthought. The key differentiator is alignment between {kw} strategy and business objectives.",
            f"This page outlines our evidence-based methodology for {kw} implementation, drawn from direct experience in the {niche} sector."
        ]
    })
    
    # Section 2: Methodology
    sections.append({
        "id": "methodology", "type": "body",
        "heading": f"Our {kw.title()} Methodology",
        "body_paragraphs": [
            f"At {brand}, our {kw} methodology follows a structured four-phase process: Assessment, Strategy, Implementation, and Validation. Each phase is designed to minimize risk while maximizing the strategic value of {kw} within your {niche} operations.",
            f"During the Assessment phase, we audit existing {kw} capabilities against industry benchmarks. The Strategy phase translates findings into a prioritized action plan aligned with your specific {svc_text} requirements.",
            f"Implementation is handled in iterative cycles, allowing for course corrections based on real-world performance data. The Validation phase establishes measurable KPIs to track the impact of {kw} on your business outcomes."
        ],
        "callout": {"type": "tip", "text": f"Our assessment process typically identifies 3-5 high-impact {kw} improvements within the first engagement session."}
    })
    
    # Section 3: Practical Application (with pain points if available)
    pain_text = ""
    if pain_points:
        pain_text = f" Common challenges we address include {', '.join(pain_points[:2])}." 
    
    sections.append({
        "id": "practical-application", "type": "body",
        "heading": f"Applying {kw.title()} Across {niche} Operations",
        "body_paragraphs": [
            f"{kw.title()} implementation varies significantly depending on organizational maturity and sector-specific requirements.{pain_text} Our team tailors each engagement to account for these variables.",
            f"For organizations early in their {kw} journey, we recommend starting with a focused pilot that demonstrates value within a single {svc_text} workstream. This builds internal buy-in and provides a baseline for scaling.",
            f"For mature organizations, we focus on optimization — identifying inefficiencies in existing {kw} processes and implementing targeted improvements that compound over time."
        ]
    })
    
    # Section 4: Why it matters
    sections.append({
        "id": "business-impact", "type": "body",
        "heading": f"The Business Impact of Strategic {kw.title()}",
        "body_paragraphs": [
            f"Organizations that invest in structured {kw} implementation report measurable improvements across key performance indicators. In our {niche} practice, we've observed consistent gains in operational efficiency, stakeholder satisfaction, and competitive positioning.",
            f"The ROI of {kw} extends beyond direct metrics. Properly implemented, it creates compounding benefits — each improvement builds on the last, creating a sustainable advantage in the {niche} marketplace."
        ],
        "callout": {"type": "note", "text": f"We establish baseline metrics at the start of every {kw} engagement so that improvements can be tracked and validated objectively."}
    })
    
    # Build multiple FAQs
    faqs = [
        {
            "question": f"How does {brand} approach {kw} differently from standard consulting?",
            "answer": f"We combine deep {niche} domain expertise with a structured, evidence-based {kw} methodology. Rather than applying generic frameworks, we tailor our approach to your specific operational context and measure outcomes against pre-established KPIs. Every engagement includes built-in validation checkpoints."
        },
        {
            "question": f"What results can I expect from a {kw} engagement?",
            "answer": f"Results depend on your starting point and objectives, but typical outcomes include improved {svc_text} efficiency, reduced operational friction, and stronger competitive positioning. We set measurable targets at the start of each engagement and track progress throughout the project lifecycle."
        },
        {
            "question": f"How long does a typical {kw} implementation take?",
            "answer": f"A focused {kw} pilot can be completed in 4-6 weeks. Full implementations typically span 3-6 months depending on scope and organizational complexity. We use an iterative approach that delivers value at each phase rather than requiring a full deployment before results are visible."
        }
    ]

    word_count = sum(len(" ".join(s.get("body_paragraphs", [])).split()) for s in sections)
    word_count += sum(len(f["answer"].split()) for f in faqs)

    return {
        "meta": {"title": brief.page_title, "description": brief.meta_description},
        "content_metadata": {"keyword": kw, "word_count": word_count, "method": "dna_synthesis"},
        "hero": hero,
        "sections": sections,
        "faq": faqs,
        "sources": ["Internal Domain Audit", f"{niche} Industry Standards", "Field Implementation Data"]
    }

def _build_expert_prompt(brief, existing_pages, site_wide_faqs) -> str:
    """
    High-Fidelity Prompt v2 with CoT, Trope Blacklist, and Business Grounding.
    """
    blacklist = "Unlock, Transform, Navigate, Delve, Landscape, Nurture, Game-changer, In conclusion, Empower, Unlock the potential, Comprehensive guide, Look no further, State-of-the-art, Cutting-edge, In today's world, Streamline"
    category = brief.niche
    
    # Build services reference
    services_ref = ""
    if brief.services:
        svc_items = []
        for s in brief.services[:4]:
            if isinstance(s, dict):
                svc_items.append(f"  - {s.get('name', s)}: {s.get('detailed_description', '')}")
            else:
                svc_items.append(f"  - {s}")
        services_ref = "\n".join(svc_items)
    
    # Build pain points reference
    pain_ref = ""
    if brief.pain_points:
        pain_ref = f"PROBLEMS THIS BUSINESS SOLVES: {', '.join(brief.pain_points[:4])}"
    
    # Build existing content reference to avoid duplication
    existing_ref = ""
    if existing_pages:
        titles = [p.get('title', p.get('url', '')) for p in existing_pages[:8]]
        existing_ref = f"EXISTING PAGES (DO NOT DUPLICATE): {', '.join(titles)}"
    
    return f"""### EXPERT PERSONA: LEAD CONSULTANT FOR {category} ###
TASK: Produce a 1200-1500 word professional document for '{brief.target_keyword}' that reads as if written by a 15-year veteran in {category}.

### PHASE 1: SILENT REASONING (DO NOT OUTPUT) ###
1. What specific business problem does '{brief.target_keyword}' solve for someone in {category}?
2. What are 3 technical details that only a practitioner would know about this topic?
3. How does this topic connect to the services listed below?
4. What would a client searching for '{brief.target_keyword}' actually need to know?

### PHASE 2: CONTENT RULES ###
BANNED PHRASES (ZERO TOLERANCE): {blacklist}
VOICE: First-person plural ("We", "Our"). Mix short declarative statements with technical depth.
SPECIFICITY: Every paragraph must contain at least ONE concrete detail (a number, a methodology name, a tool, a benchmark, or a real-world scenario).
GROUNDING: Content MUST reference at least 2 of these actual services:
{services_ref or '  - (No specific services provided)'}
{pain_ref}
TONE: {brief.tone} Authority — confident but not salesy.
STRUCTURE: Minimum 4 sections with 2-3 paragraphs each. Dense, no filler.

### BRAND IDENTITY ###
{brief.site_profile_md}

{existing_ref}

### OUTPUT FORMAT: STRICT JSON ###
{{
  "meta": {{"title": "{brief.page_title}", "description": "Expert practitioner insights on {brief.target_keyword} for {category} professionals"}},
  "content_metadata": {{"keyword": "{brief.target_keyword}", "word_count": <int>, "expertise_level": "Professional"}},
  "hero": {{
    "headline": "A specific, non-generic headline about {brief.target_keyword} (NOT 'The Ultimate Guide')",
    "subheadline": "A concrete value statement mentioning a measurable outcome"
  }},
  "sections": [
     {{
       "id": "unique-kebab-id", "type": "body",
       "heading": "Specific technical heading (not just '{brief.target_keyword}')",
       "body_paragraphs": [
         "Dense paragraph 1 with specific details (80-120 words)",
         "Dense paragraph 2 with methodology or framework reference (80-120 words)",
         "Dense paragraph 3 with practical application (80-120 words)"
       ],
       "callout": {{"type": "tip", "text": "A specific, actionable technical tip"}}
     }}
  ],
  "faq": [
     {{"question": "A question a real client would ask during a consultation?", "answer": "An 80-120 word authoritative answer with specific details, methodology references, and measurable claims."}},
     {{"question": "Second expert question?", "answer": "Detailed answer"}},
     {{"question": "Third expert question?", "answer": "Detailed answer"}}
  ],
  "sources": ["Industry standard or framework name", "Technical documentation reference"]
}}

CRITICAL: Generate at minimum 4 sections and 3 FAQs. Each FAQ answer must be 80-120 words.
"""

def _extract_json_from_llm(text: str) -> dict:
    """Robust extraction."""
    try:
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match: return json.loads(match.group(1))
        return json.loads(text)
    except: return None

def render_content_to_html(schema: dict) -> str:
    """HTML Synthesis for web deployment."""
    meta = schema.get("meta", {})
    hero = schema.get("hero", {})
    sections = schema.get("sections", [])
    
    html = f"<h1>{hero.get('headline')}</h1><p>{hero.get('subheadline')}</p>"
    for sec in sections:
        html += f"<h2>{sec.get('heading')}</h2>"
        for p in sec.get("body_paragraphs", []): html += f"<p>{p}</p>"
        if sec.get("callout"): html += f"<blockquote>{sec['callout']['text']}</blockquote>"
    
    if schema.get("faq"):
        html += "<h2>Frequently Asked Questions</h2>"
        for f in schema["faq"]:
            html += f"<h3>{f['question']}</h3><p>{f['answer']}</p>"
            
    return f"<!DOCTYPE html><html><head><title>{meta.get('title')}</title></head><body>{html}</body></html>"

def render_content_to_react(schema: dict) -> str:
    """React Component Synthesis."""
    return f"export default function Page() {{ return (<article>{render_content_to_html(schema)}</article>); }}"

def _call_openai(prompt, config):
    import openai
    api_key = config.get("api_key", "")
    model = config.get("model", "gpt-4o-mini")
    
    if hasattr(openai, "OpenAI"):
        client = openai.OpenAI(api_key=api_key)
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": "You are a lead consultant. Never use AI tropes."}, {"role": "user", "content": prompt}],
            temperature=0.7
        )
        return res.choices[0].message.content
    else:
        openai.api_key = api_key
        res = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": "You are a lead consultant. Never use AI tropes."}, {"role": "user", "content": prompt}],
            temperature=0.7
        )
        return res['choices'][0]['message']['content']

def _call_gemini(prompt, config):
    import google.generativeai as genai
    import httpx
    original_model = config.get("model", "gemini-1.5-flash")
    model_candidates = [original_model, "gemini-2.0-flash", "gemini-flash-latest", "gemini-1.5-flash", "gemini-pro-latest", "gemini-pro"]
    model_candidates = list(dict.fromkeys(model_candidates))
    
    key = config.get('api_key', '')
    if not key:
        raise RuntimeError("Gemini API Key is missing.")

    max_retries = 5
    base_delay = 5.0

    for attempt in range(max_retries):
        # SDK Try
        try:
            genai.configure(api_key=key)
            for model_name in model_candidates:
                target_model = model_name if model_name.startswith("models/") else f"models/{model_name}"
                try:
                    model = genai.GenerativeModel(target_model)
                    res = model.generate_content(prompt)
                    if res and res.text: return res.text
                except Exception as e:
                    if "404" in str(e): continue
                    if "429" in str(e): raise e # Jump to retry loop
                    raise e
        except Exception as sdk_err:
            if "429" not in str(sdk_err):
                logger.warning(f"Gemini SDK failed: {sdk_err}. Trying Direct REST Handshake...")

        # REST Try
        for model_name in model_candidates:
            clean_model = model_name.replace("models/", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={key}"
            try:
                payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}}
                res = httpx.post(url, json=payload, timeout=60.0)
                if res.status_code == 200:
                    data = res.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
                elif res.status_code == 404:
                    continue
                elif res.status_code == 429:
                    # Exponential Backoff with jitter
                    retry_info = res.json().get("error", {}).get("details", [{}])[0].get("retryDelay", f"{base_delay * (2 ** attempt)}s")
                    wait_time = float(retry_info.replace("s", "")) if "s" in str(retry_info) else base_delay * (2 ** attempt)
                    wait_time = min(wait_time, 60.0) # Cap at 60s
                    logger.warning(f"Gemini Rate Limit (429). Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time + random.uniform(2, 5))
                    break # Break model loop to retry with fresh attempt
                elif res.status_code == 403:
                    raise RuntimeError("Gemini API 403: Access Denied. Check 'Generative Language API' enablement.")
                else:
                    raise RuntimeError(f"Gemini REST Error {res.status_code}: {res.text}")
            except Exception as rest_err:
                if "429" in str(rest_err):
                    time.sleep(base_delay * (2 ** attempt))
                    break
                if "404" in str(rest_err): continue
                raise rest_err
    
    raise RuntimeError(f"Gemini API 429: Quota exhausted after {max_retries} retries. Please check your billing/usage limits in Google AI Studio.")

def _call_ollama(prompt, config):
    import httpx
    import time
    host = config.get('ollama_host', 'http://localhost:11434').rstrip('/')
    model = config.get("ollama_model", "llama3")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = httpx.post(
                f"{host}/api/generate", 
                json={"model": model, "prompt": prompt, "stream": False}, 
                timeout=300.0
            )
            if res.status_code == 200:
                return res.json().get("response", "")
            elif res.status_code == 500 and "terminated" in res.text:
                logger.warning(f"Ollama runner terminated (Attempt {attempt+1}/{max_retries}). Retrying in 5s...")
                time.sleep(5)
                continue
            elif res.status_code == 404:
                logger.error(f"Ollama Error: Model '{model}' not found on {host}.")
                return f"Error: Ollama model '{model}' not found."
            else:
                logger.error(f"Ollama Error {res.status_code}: {res.text}")
                return f"Error: Ollama returned {res.status_code}"
        except httpx.ConnectError:
            logger.error(f"Ollama Error: Could not connect to {host}. Is Ollama running?")
            return "Error: Could not connect to Ollama."
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Ollama Exception: {e}. Retrying...")
                time.sleep(2)
                continue
            logger.error(f"Ollama Exception: {str(e)}")
            return f"Error: {str(e)}"
    
    return "Error: Ollama runner terminated repeatedly."

def _call_openrouter(prompt, config):
    import httpx
    api_key = config.get("api_key")
    model = config.get("model", "google/gemini-2.0-flash-001")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://urlforge.ai",
        "X-Title": "UrlForge",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional SEO consultant. Use clean markdown."},
            {"role": "user", "content": prompt}
        ]
    }
    
    res = httpx.post(url, headers=headers, json=payload, timeout=120)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content']
    else:
        raise RuntimeError(f"OpenRouter Error {res.status_code}: {res.text}")
