# src/modules/internal_links.py

from collections import defaultdict


MIN_INCOMING_LINKS = 2
MAX_SUGGESTIONS_PER_PAGE = 5


def run(context):

    graph = context["graph"]
    pages = context["pages"]

    issues = {
        "orphan_pages": [],
        "low_internal_links": []
    }

    suggestions = defaultdict(list)

    all_pages = graph.pages()

    # ---------
    # detect orphan pages
    # ---------
    for url in all_pages:

        incoming = graph.get_incoming(url)

        if len(incoming) == 0:
            issues["orphan_pages"].append(url)

        elif len(incoming) < MIN_INCOMING_LINKS:
            issues["low_internal_links"].append(url)

    # ---------
    # generate link suggestions
    # ---------
    for target in issues["low_internal_links"] + issues["orphan_pages"]:

        incoming = graph.get_incoming(target)

        # candidate pages to link from
        candidates = [
            p for p in all_pages
            if p != target and target not in graph.get_outgoing(p)
        ]

        for source in candidates[:MAX_SUGGESTIONS_PER_PAGE]:

            suggestions[target].append({
                "from": source,
                "to": target
            })

    return {
        "issues": issues,
        "suggestions": dict(suggestions)
    }
