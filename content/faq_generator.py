# src/content/faq_generator.py
"""
Expert FAQ Generator (v2 - Quality Overhaul).
Produces high-fidelity, business-specific FAQs that:
1. Reference actual services/products from the site
2. Use industry-specific terminology (not generic filler)
3. Answer with actionable detail, not vague platitudes
4. Pass as human-written expert content

Uses cascading LLM fallback and deep fragment synthesis for offline mode.
"""

import re
import json
from collections import Counter
from bs4 import BeautifulSoup
from src.utils.logger import logger
from src.content.content_schema import FAQItem


def generate_site_faqs(site_keywords, domain, llm_config, site_context=None):
    """
    Expert FAQ pipeline: API-First with full fallback chain, Fragment-Synthesis Fallback.
    """
    logger.info(f"FaqEngine v2: Synthesizing expert Q&A for {domain}")
    site_context = site_context or {}
    
    # Group keywords that belong together before passing to generator
    from src.content.phrase_extractor import group_related_keywords
    if site_keywords:
        site_keywords = group_related_keywords(site_keywords)
    
    faqs = []
    
    # Try LLM generation with full fallback chain
    from src.utils.llm_resolver import resolve_api_key, is_valid_key
    resolved_provider, resolved_key = resolve_api_key(llm_config)
    has_api = is_valid_key(resolved_key) or resolved_provider == "ollama"
    
    if has_api:
        faqs = _generate_faqs_with_llm(site_keywords, domain, llm_config, site_context)
    
    if not faqs:
        logger.info(f"FaqEngine v2: API unavailable or failed. Using Fragment Synthesis for {domain}")
        faqs = _synthesize_faqs_from_fragments(site_keywords, domain, site_context)

    # ── Quality Validation ────────────────────────────────────────────
    robust_faqs = []
    for item in faqs[:10]:
        q, a = item.get("question", ""), item.get("answer", "")
        
        # Quality gates
        if len(q) < 15:
            continue
        if len(a) < 40:
            continue
        # Reject generic AI filler
        if _is_generic_faq(q, a, domain):
            continue
        # Ensure question is actually a question
        if "?" not in q:
            q = q.rstrip(".") + "?"
        
        robust_faqs.append(FAQItem(question=q, answer=a))
    
    # If we filtered too many, supplement with high-quality synthetics
    if len(robust_faqs) < 5:
        supplemental = _generate_supplemental_faqs(site_keywords, domain, site_context, len(robust_faqs))
        for item in supplemental:
            if len(robust_faqs) >= 8:
                break
            q, a = item.get("question", ""), item.get("answer", "")
            if len(q) > 15 and len(a) > 40:
                robust_faqs.append(FAQItem(question=q, answer=a))
            
    return robust_faqs


def _generate_faqs_with_llm(keywords, domain, llm_config, site_context):
    """High-Fidelity Expert LLM FAQ Generation with full fallback chain."""
    
    niche = site_context.get("niche", "")
    mission = site_context.get("mission", "")
    category = site_context.get("category", niche)
    services = site_context.get("services", [])
    pain_points = site_context.get("pain_points", [])
    company_name = site_context.get("company_name", domain)
    target_audience = site_context.get("target_audience", [])
    
    # Build services text from actual site data
    services_text = ""
    if services:
        for s in services[:5]:
            if isinstance(s, dict):
                services_text += f"  - {s.get('name', '')}: {s.get('detailed_description', '')}\n"
            else:
                services_text += f"  - {s}\n"
    
    # Build keywords text (phrases kept together)
    kw_text = ", ".join(keywords[:10]) if keywords else "general topics"
    
    prompt = f"""ROLE: You are the Chief Knowledge Officer at {company_name} ({domain}), operating in {category}.

TASK: Write 8 Expert-Level FAQ entries that demonstrate deep domain expertise. Each FAQ must sound like it was written by a veteran professional in {category}, NOT by a content writer.

BUSINESS CONTEXT:
- Company: {company_name}
- Category: {category}
- Niche: {niche}
- Mission: {mission}
- Key Topics: {kw_text}
- Services:
{services_text or '  - Not specified'}
- Pain Points: {', '.join(pain_points[:5]) if pain_points else 'Not specified'}
- Target Audience: {', '.join(target_audience[:3]) if target_audience else 'Professionals'}

STRICT QUALITY RULES:
1. FORBIDDEN WORDS/PHRASES (instant rejection): "unlock", "transform", "navigate", "delve", "landscape", "empower", "leverage", "comprehensive", "streamline", "cutting-edge", "state-of-the-art", "game-changer", "look no further", "in today's world"
2. NO DEFINITIONS: Do NOT explain what a keyword is. Explain HOW {company_name} applies it, what problems it solves, and what outcomes clients can expect.
3. SPECIFICITY REQUIREMENT: Every answer must mention at least ONE specific:
   - Technical detail, methodology, or framework
   - Measurable outcome or metric
   - Industry-specific term or standard
4. ANSWER LENGTH: Each answer must be 80-150 words. Dense, no filler.
5. QUESTION QUALITY: Questions must be the kind a REAL client or prospect would ask during a sales call or project consultation, NOT generic "What is X?" questions.
6. BUSINESS GROUNDING: Reference actual {company_name} services, processes, or methodologies where possible.

QUESTION PATTERNS TO USE:
- "How does [company] handle [specific scenario]?"
- "What's the typical process for [service] at [company]?"
- "What results can I expect from [service]?"
- "How does [company]'s approach to [topic] differ from standard practices?"
- "What should I consider before investing in [service]?"
- "How does [company] ensure [quality/security/performance] in [area]?"

OUTPUT: Return a JSON array. Nothing else.
[
  {{"question": "Specific expert question?", "answer": "Dense, authoritative 80-150 word answer with technical specifics."}},
  ...
]
"""
    try:
        from src.utils.llm_resolver import call_llm_with_fallback
        res = call_llm_with_fallback(prompt, llm_config)
        data = _extract_json_from_llm_response(res)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"FAQ LLM failed: {e}")
        return []


def _synthesize_faqs_from_fragments(keywords, domain, site_context):
    """
    High-Quality Offline FAQ Synthesis.
    Builds FAQs by intelligently pairing site data signals with question templates.
    Each FAQ must reference actual services, technologies, or business attributes.
    """
    faqs = []
    mission = site_context.get("mission", "")
    services = site_context.get("services", [])
    niche = site_context.get("niche", "Expert Industry")
    category = site_context.get("category", niche)
    company_name = site_context.get("company_name", domain)
    pain_points = site_context.get("pain_points", [])
    technologies = site_context.get("technologies", [])
    target_audience = site_context.get("target_audience", [])
    
    # ── Strategy 1: Service-Specific Q&A (Highest Quality) ────────────
    for i, s in enumerate(services[:4]):
        name = s.get("name") if isinstance(s, dict) else str(s)
        desc = s.get("detailed_description", "") if isinstance(s, dict) else ""
        
        if desc and len(desc) > 20:
            answer = f"At {company_name}, our {name} service is built around {desc}. We approach each engagement with a structured methodology that begins with assessment and ends with measurable results. Our team in the {niche} space ensures that every {name} project aligns with industry standards and delivers tangible ROI for our clients."
        elif mission and len(mission) > 20:
            answer = f"{company_name} provides {name} as a core part of our {category} operations. {mission} Our team brings hands-on experience in {niche} to every {name} engagement, ensuring outcomes are both technically sound and commercially viable."
        else:
            answer = f"Our {name} offering at {company_name} is designed specifically for professionals in the {niche} sector. We combine proven methodologies with practical field experience to deliver {name} solutions that produce measurable improvements. Each engagement follows a structured process from initial assessment through implementation and verification."
        
        faqs.append({
            "question": f"What can I expect from {company_name}'s {name} service?",
            "answer": answer
        })
    
    # ── Strategy 2: Pain Point Q&A ────────────────────────────────────
    for pp in pain_points[:2]:
        if len(faqs) >= 8:
            break
        faqs.append({
            "question": f"How does {company_name} address {pp.lower()}?",
            "answer": f"Addressing {pp.lower()} is central to our work at {company_name}. In the {category} space, this challenge typically stems from misaligned processes or outdated tooling. Our approach starts with a diagnostic assessment to identify root causes, followed by targeted interventions using our {niche} expertise. Clients typically see measurable improvements within the first engagement cycle."
        })
    
    # ── Strategy 3: Technology/Methodology Q&A ────────────────────────
    if technologies:
        tech_list = ", ".join(technologies[:4])
        faqs.append({
            "question": f"What technologies and tools does {company_name} work with?",
            "answer": f"{company_name} maintains deep expertise in {tech_list} among other industry-standard tools. Our technology choices are driven by project requirements, not trends. In the {niche} sector, we prioritize technologies that offer reliability, scalability, and strong community support. Every implementation undergoes our internal validation process before client deployment."
        })
    
    # ── Strategy 4: Audience-Specific Q&A ─────────────────────────────
    if target_audience:
        audience_text = " and ".join(target_audience[:2])
        faqs.append({
            "question": f"Is {company_name} the right fit for {audience_text}?",
            "answer": f"{company_name} has built its practice specifically around the needs of {audience_text}. Our experience in {category} means we understand the unique challenges, compliance requirements, and operational constraints that {audience_text} face. Whether you're scaling operations or addressing a specific technical gap, our team can provide tailored {niche} solutions with clear deliverables and timelines."
        })
    
    # ── Strategy 5: Keyword-Driven Q&A ────────────────────────────────
    for kw in keywords[:3]:
        if len(faqs) >= 8:
            break
        # Use the keyword as-is (it's already a meaningful phrase)
        faqs.append({
            "question": f"How does {company_name} approach {kw.title()} in practice?",
            "answer": f"At {company_name}, {kw.title()} is integrated into our core {category} methodology rather than treated as an isolated concern. Our practitioners apply {kw} principles throughout the project lifecycle — from initial planning through delivery and ongoing optimization. This ensures consistency and allows us to track the impact of {kw} on project outcomes quantitatively."
        })
        
    return faqs


def _generate_supplemental_faqs(keywords, domain, site_context, existing_count):
    """Generate additional quality FAQs when filtering removed too many."""
    faqs = []
    niche = site_context.get("niche", "our field")
    company_name = site_context.get("company_name", domain)
    category = site_context.get("category", niche)
    
    templates = [
        {
            "question": f"What makes {company_name}'s approach different from competitors in {niche}?",
            "answer": f"{company_name} differentiates through a methodology-first approach to {category}. Rather than applying one-size-fits-all solutions, we conduct thorough assessments and design custom strategies that align with each client's specific objectives. Our team's direct field experience in {niche} means we can anticipate challenges and build solutions that scale with your business."
        },
        {
            "question": f"How do I get started working with {company_name}?",
            "answer": f"The typical engagement with {company_name} begins with a discovery consultation where we assess your current {niche} needs and define clear objectives. From there, we develop a scoped proposal with deliverables, timelines, and measurable success criteria. Our process is designed to minimize disruption while maximizing the strategic value of every {category} initiative."
        },
        {
            "question": f"What kind of results has {company_name} delivered for clients in {category}?",
            "answer": f"Our clients in the {category} space consistently report measurable improvements after working with {company_name}. Results vary by engagement type, but typically include enhanced operational efficiency, reduced technical debt, and stronger competitive positioning. We establish baseline metrics at the start of every project so improvements can be tracked and validated objectively."
        },
        {
            "question": f"How does {company_name} ensure quality and accountability in {niche} projects?",
            "answer": f"Quality assurance at {company_name} is built into every phase of our {niche} delivery process. We use structured review checkpoints, automated validation where applicable, and transparent reporting to keep stakeholders informed. Our team follows industry-standard frameworks adapted for {category}, ensuring that every deliverable meets professional benchmarks before client handoff."
        },
    ]
    
    # Return only what's needed to fill the gap
    needed = max(0, 5 - existing_count)
    return templates[:needed]


def _is_generic_faq(question: str, answer: str, domain: str) -> bool:
    """
    Detect if a FAQ is too generic/AI-sounding to be useful.
    Returns True if it should be rejected.
    """
    q_lower = question.lower()
    a_lower = answer.lower()
    
    # Reject pure definition questions
    definition_starts = ["what is ", "what are ", "define ", "explain "]
    if any(q_lower.startswith(ds) for ds in definition_starts):
        # Only reject if the answer is also generic (doesn't mention the domain)
        if domain.lower().split('.')[0] not in a_lower:
            return True
    
    # Reject AI-trope-heavy answers
    ai_tropes = ["unlock", "transform", "navigate", "delve", "landscape", 
                  "empower", "in today's", "game-changer", "look no further",
                  "comprehensive solution", "cutting-edge"]
    trope_count = sum(1 for trope in ai_tropes if trope in a_lower)
    if trope_count >= 2:
        return True
    
    # Reject very short, low-effort answers
    if len(answer) < 50:
        return True
    
    return False


def _extract_json_from_llm_response(text: str):
    """Robust JSON extraction from LLM response — handles arrays and objects."""
    if not text:
        return None
    try:
        # Try direct parse first
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Try to find JSON array
    array_match = re.search(r'\[[\s\S]*\]', text)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object
    obj_match = re.search(r'\{[\s\S]*\}', text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None
