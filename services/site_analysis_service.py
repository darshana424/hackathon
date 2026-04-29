# src/services/site_analysis_service.py
"""
Enhanced Business Analysis Synthesizer (v2).
Produces deep, accurate business intelligence by:
1. Cascading LLM key resolution (if one field empty, tries others)
2. Richer context extraction with structured page data 
3. Stronger prompts that force industry-specific output
4. Multi-signal validation to prevent generic "Professional Services" fallback
"""

from src.content.page_generator import _call_openai, _call_gemini, _call_ollama, _call_openrouter, _extract_json_from_llm
from src.utils.llm_resolver import resolve_api_key, is_valid_key, call_llm_with_fallback
from src.config import config
from src.utils.logger import logger
import json
import re


def synthesize_business_analysis(domain: str, structured_data: list, llm_config: dict = None) -> dict:
    """
    Takes all structured chunks and synthesizes them into a final report and generation context.
    
    v2 Improvements:
    - Cascading API key resolution via llm_resolver
    - Enriched prompt with explicit anti-generic guardrails
    - Extracts real services/products from structured data before prompting
    - Falls back to deep heuristic analysis if LLM unavailable
    """
    logger.info(f"Synthesizing final business analysis for {domain}...")
    
    # ── Pre-Analysis: Extract concrete signals from structured data ─────
    pre_analysis = _pre_analyze_structured_data(structured_data, domain)
    
    # Flatten the data for the LLM, but cap size to avoid token overflow
    combined_context = json.dumps(structured_data[:10], indent=2)[:8000]
    
    prompt = f"""### DEEP STRATEGIC BUSINESS AUDIT ###
You are a World-Class Business Consultant conducting a deep strategic audit of {domain}.

Your goal is to capture the "SOUL" and "TOUCH" of this business. Do NOT provide a generic AI summary. We need the unique essence that makes this business different from 10,000 others in the same sector.

EXTRACTED SITE DATA:
{combined_context}

PRE-ANALYSIS SIGNALS:
- Primary Services: {', '.join(pre_analysis['detected_services'][:10]) or 'None found'}
- Core Technologies: {', '.join(pre_analysis['detected_technologies'][:10]) or 'None found'}
- Detected Personality: {', '.join(pre_analysis['detected_personalities'][:8]) or 'None found'}
- Detected Tonality: {', '.join(pre_analysis['detected_tonalities'][:5]) or 'None found'}
- Detected Brand Name: {pre_analysis.get('company_name', 'Unknown')}
- Key Value Props: {', '.join(pre_analysis['value_propositions'][:8]) or 'None found'}
- Target Segments: {', '.join(pre_analysis['target_audience'][:8]) or 'None found'}

STRICT AUDIT RULES:
1. CAPTURE THE TOUCH: What is the specific 'vibe' or 'personality' of this brand? (e.g., Is it 'Rugged industrial reliability', 'Hyper-modern minimalist tech', 'Compassionate boutique care', 'Aggressive high-growth disruption'?)
2. HYPER-SPECIFIC CATEGORY: NEVER use generic terms like "Agency", "Company", or "Consultancy". 
   - BAD: "Marketing Agency" → GOOD: "Performance-Driven B2B SaaS Growth Accelerator"
   - BAD: "Law Firm" → GOOD: "Boutique Intellectual Property Protection for Deep-Tech Startups"
3. NO HALLUCINATIONS: Use the ACTUAL names of services and technologies found in the data.
4. EMOTIONAL HOOK: What is the core emotional reason a client chooses them over a cheaper competitor?

REPORT STRUCTURE:
# Strategic Brand Audit: {domain}

## The Essence (Executive Summary)
[Capture the "Touch" here. 2-3 sentences that define their unique place in the market. Avoid corporate jargon.]

## Core Service Pillars
[List specific services with detailed, expert-level descriptions. Mention specific methodologies if found.]

## Brand Persona & Narrative
[Describe their brand voice and the story they are telling. What is their unique 'Touch'?]

## Target Market & Specific Audience
[Who exactly are they talking to? What are the specific psychographics?]

## Technical Backbone
[Specific technologies and tools that power their value proposition.]

## Unique Differentiators (The "Touch")
[What makes them unique? What is the one thing they do that others don't?]

---

JSON STRATEGIC BLOCK (Return at the end):
```json
{{
  "company_name": "Actual brand name",
  "category": "Hyper-specific descriptor (5-10 words)",
  "niche": "The micro-niche descriptor",
  "brand_personality": "3-5 adjectives describing their 'Touch'",
  "emotional_hook": "The core psychological driver for their clients",
  "tone": "The detected brand voice (e.g. 'Gritty and Direct', 'Polished and Corporate')",
  "mission": "Their actual stated purpose",
  "primary_purpose": "Single sentence defining why they exist",
  "services": [
    {{"name": "Specific Service", "detailed_description": "2-sentence expert description"}}
  ],
  "target_audience": ["Segment 1", "Segment 2"],
  "technologies": ["Tech 1", "Tech 2"],
  "pain_points": ["Specific problem 1", "Specific problem 2"],
  "value_propositions": ["Unique claim 1", "Unique claim 2"]
}}
```
"""

    # ── Resolve LLM config with cascading fallback ─────────────────────
    if not llm_config:
        llm_config = {
            "provider": config.LLM_PROVIDER,
            "api_key": config.OPENAI_API_KEY.get_secret_value() if config.OPENAI_API_KEY else None,
            "gemini_key": config.GEMINI_API_KEY.get_secret_value() if config.GEMINI_API_KEY else None,
            "model": "gpt-4o-mini" if config.LLM_PROVIDER == "openai" else "gemini-1.5-flash"
        }
    
    # Use centralized resolver — cascading field fallback
    resolved_provider, resolved_key = resolve_api_key(llm_config)
    has_api = is_valid_key(resolved_key) or resolved_provider == "ollama"

    if has_api:
        try:
            raw_response = call_llm_with_fallback(prompt, llm_config)
            
            # Extract JSON and Markdown
            context = _extract_json_from_llm(raw_response) or {}
            
            # Validate the context is not generic
            context = _validate_and_enrich_context(context, pre_analysis, domain)
            
            # Strip JSON from markdown report
            report = raw_response
            report = re.sub(r'```json\s*\{.*?\}\s*```', '', report, flags=re.DOTALL).strip()
            report = re.sub(r'\{[^{}]*"category"[^{}]*\}', '', report, flags=re.DOTALL).strip()
            
            return {
                "report": report,
                "context": context
            }
        except Exception as e:
            logger.error(f"LLM Synthesis failed: {e}. Using heuristic analysis.")
    
    # ── Heuristic Fallback: Deep analysis without LLM ─────────────────
    logger.info(f"Building heuristic business analysis for {domain}")
    return _build_heuristic_analysis(domain, structured_data, pre_analysis)


def _pre_analyze_structured_data(structured_data: list, domain: str) -> dict:
    """
    Extract concrete signals from structured data BEFORE sending to LLM.
    This provides ground truth for validation and enrichment.
    """
    services = set()
    technologies = set()
    value_props = set()
    audiences = set()
    personalities = set()
    tonalities = set()
    company_name = ""
    missions = []
    
    for chunk in structured_data:
        if not isinstance(chunk, dict):
            continue
        
        # Extract services
        for svc in chunk.get("core_services", []):
            if isinstance(svc, str) and len(svc) > 3:
                services.add(svc.strip())
        
        # Extract personalities and tonalities
        for p in chunk.get("brand_personality", []):
            if isinstance(p, str): personalities.add(p.strip())
        
        tonality = chunk.get("tonality")
        if isinstance(tonality, str): tonalities.add(tonality.strip())
        
        # Extract technologies
        for tech in chunk.get("technologies_mentioned", []):
            if isinstance(tech, str) and len(tech) > 1:
                technologies.add(tech.strip())
        
        # Extract value propositions
        for vp in chunk.get("value_propositions", []):
            if isinstance(vp, str) and len(vp) > 5:
                value_props.add(vp.strip())
        
        # Extract target audience
        for aud in chunk.get("target_audience", []):
            if isinstance(aud, str) and len(aud) > 3:
                audiences.add(aud.strip())
        
        # Extract company info
        company_info = chunk.get("company_info", {})
        if isinstance(company_info, dict):
            name = company_info.get("name", "")
            if name and len(name) > 2 and name.lower() not in {"unknown", "n/a", "none"}:
                company_name = name
            mission = company_info.get("mission", "")
            if mission and len(mission) > 10:
                missions.append(mission)
        
        # Extract key findings
        for finding in chunk.get("key_findings", []):
            if isinstance(finding, str) and len(finding) > 10:
                # Check if it's a service/product description
                if any(kw in finding.lower() for kw in ["offer", "provide", "specialize", "service", "product", "solution"]):
                    services.add(finding.strip())
    
    return {
        "detected_services": list(services),
        "detected_technologies": list(technologies),
        "value_propositions": list(value_props),
        "target_audience": list(audiences),
        "detected_personalities": list(personalities),
        "detected_tonalities": list(tonalities),
        "company_name": company_name,
        "missions": missions,
    }


def _validate_and_enrich_context(context: dict, pre_analysis: dict, domain: str) -> dict:
    """
    Validate LLM output against pre-analysis signals.
    Replace generic labels with concrete data where available.
    """
    # Validate category — reject overly generic ones
    generic_categories = {
        "professional services", "technology company", "digital solutions", 
        "business services", "general", "unknown", "it services",
        "web development", "software company", "tech company",
        "consulting", "digital agency", "online business"
    }
    
    category = context.get("category", "").strip()
    if category.lower() in generic_categories or len(category) < 5:
        # Try to build a better category from pre-analysis
        if pre_analysis["detected_services"]:
            primary_service = pre_analysis["detected_services"][0]
            if pre_analysis["detected_technologies"]:
                category = f"{primary_service} ({pre_analysis['detected_technologies'][0]})"
            else:
                category = primary_service
        elif pre_analysis["detected_technologies"]:
            category = f"{pre_analysis['detected_technologies'][0]} Platform"
        context["category"] = category
    
    # Enrich services if LLM returned empty/generic
    llm_services = context.get("services", [])
    if not llm_services or (isinstance(llm_services, list) and len(llm_services) < 2):
        if pre_analysis["detected_services"]:
            context["services"] = [
                {"name": svc, "detailed_description": f"Core service offering of {domain}"}
                for svc in pre_analysis["detected_services"][:6]
            ]
    
    # Set company name if detected
    if pre_analysis["company_name"] and not context.get("company_name"):
        context["company_name"] = pre_analysis["company_name"]
    
    # Use actual mission if LLM hallucinated one
    if pre_analysis["missions"] and context.get("mission"):
        # Check if LLM mission looks generic
        llm_mission = context["mission"].lower()
        generic_missions = ["provide", "deliver", "offer", "empower", "help businesses"]
        if any(g in llm_mission for g in generic_missions) and len(llm_mission) < 50:
            context["mission"] = pre_analysis["missions"][0]
    
    # Ensure brand touch markers are present
    if not context.get("brand_personality") and pre_analysis.get("detected_personalities"):
        context["brand_personality"] = pre_analysis["detected_personalities"][:5]
    
    if not context.get("emotional_hook"):
        context["emotional_hook"] = "Professional authority and domain-specific excellence"
    
    # Ensure domain is set
    context["domain"] = domain
    
    return context


def _build_heuristic_analysis(domain: str, structured_data: list, pre_analysis: dict) -> dict:
    """
    Deep heuristic analysis when no LLM is available.
    Uses pre-analyzed signals to build the most accurate profile possible.
    """
    services = pre_analysis["detected_services"]
    technologies = pre_analysis["detected_technologies"]
    company_name = pre_analysis["company_name"] or domain.split('.')[0].title()
    missions = pre_analysis["missions"]
    
    # Build category from strongest signal
    if services:
        category = services[0]
        if technologies:
            category = f"{services[0]} ({technologies[0]})"
    elif technologies:
        category = f"{technologies[0]} Solutions"
    else:
        category = f"{domain.split('.')[0].title()} Services"
    
    # Build niche
    niche = " & ".join(services[:3]) if services else category
    
    # Mission
    mission = missions[0] if missions else f"{company_name} specializes in {niche}."
    
    # Build report
    report = f"# Business Intelligence Report: {domain}\n\n"
    report += f"## Executive Summary\n"
    report += f"{company_name} operates in the **{category}** space"
    if services:
        report += f", offering {', '.join(services[:3])}"
    report += ".\n\n"
    
    report += f"## Core Service Offerings\n"
    for svc in services[:6]:
        report += f"- **{svc}**\n"
    if not services:
        report += f"- Services not clearly identified from site content.\n"
    
    report += f"\n## Technical Stack\n"
    for tech in technologies[:8]:
        report += f"- {tech}\n"
    if not technologies:
        report += f"- No specific technologies detected.\n"
    
    report += f"\n## Brand Mission\n{mission}\n"
    
    report += f"\n---\n*Heuristic analysis — LLM-enhanced analysis available with API configuration.*"
    
    # Build context
    context = {
        "category": category,
        "niche": niche,
        "brand_personality": pre_analysis.get("detected_personalities", [])[:5],
        "emotional_hook": "Professional reliability and domain expertise",
        "mission": mission,
        "tone": "Professional",
        "primary_purpose": f"{company_name} provides {niche} services.",
        "services": [{"name": s, "detailed_description": ""} for s in services[:6]],
        "target_audience": pre_analysis["target_audience"][:5],
        "technologies": technologies[:8],
        "pain_points": [],
        "value_propositions": pre_analysis["value_propositions"][:5],
        "company_name": company_name,
        "domain": domain
    }
    
    return {
        "report": report,
        "context": context
    }
