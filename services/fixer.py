from urllib.parse import urlparse


def fix_url(url: str) -> str:
    # Remove query params
    url = url.split("?")[0]

    # Force HTTPS
    if url.startswith("http://"):
        url = url.replace("http://", "https://")

    # Remove trailing slash (except root)
    parsed = urlparse(url)
    if parsed.path != "/" and url.endswith("/"):
        url = url.rstrip("/")

    return url


def fix_urls(clean_urls):
    fixed = set()

    for url in clean_urls:
        try:
            fixed.add(fix_url(url))
        except:
            continue

    return list(fixed)


def generate_fixed_sitemap(urls):
    # Already cleaned URLs → just return for generator
    return urls


def generate_fix_report(audit):
    fixes = []

    if audit["issues"].get("duplicates"):
        fixes.append("Removed duplicate URLs")

    if audit["issues"].get("has_query_params"):
        fixes.append("Removed query parameters from URLs")

    if audit["issues"].get("not_https"):
        fixes.append("Converted all URLs to HTTPS")

    if audit["issues"].get("excluded_from_sitemap"):
        fixes.append("Included important pages in sitemap")

    if audit["issues"].get("non_200"):
        fixes.append("Removed broken/non-200 pages from sitemap")

    return fixes
