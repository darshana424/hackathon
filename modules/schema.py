from bs4 import BeautifulSoup
from urllib.parse import urlparse
import datetime


def run(context):

    pages = context["pages"]
    domain = context["domain"]

    issues = []
    schemas = {}

    for page in pages:

        url = page.get("url")
        html = page.get("html")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")

        existing_schema = soup.find("script", {"type": "application/ld+json"})

        if existing_schema:
            continue

        schema = detect_schema_type(soup, url, domain)

        if schema:

            schemas[url] = schema

            issues.append({
                "url": url,
                "issue": "missing_schema"
            })

    return {
        "issues": issues,
        "schemas": schemas
    }


def detect_schema_type(soup, url, domain):

    title = extract_title(soup)
    description = extract_description(soup)
    images = extract_images(soup)

    path = urlparse(url).path

    if "/blog" in path or "article" in path:
        return build_article_schema(url, title, description, images)

    if "/product" in path:
        return build_product_schema(url, title, description, images)

    return build_webpage_schema(url, title, description)


def extract_title(soup):

    title_tag = soup.find("title")

    if title_tag:
        return title_tag.text.strip()

    h1 = soup.find("h1")

    if h1:
        return h1.text.strip()

    return "Untitled Page"


def extract_description(soup):

    meta = soup.find("meta", attrs={"name": "description"})

    if meta and meta.get("content"):
        return meta.get("content")

    p = soup.find("p")

    if p:
        return p.text.strip()[:155]

    return ""


def extract_images(soup):

    images = []

    for img in soup.find_all("img", src=True):

        images.append(img["src"])

        if len(images) >= 3:
            break

    return images


def build_article_schema(url, title, description, images):

    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "image": images,
        "datePublished": datetime.datetime.utcnow().isoformat(),
        "mainEntityOfPage": url
    }


def build_product_schema(url, title, description, images):

    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "description": description,
        "image": images,
        "url": url
    }


def build_webpage_schema(url, title, description):

    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": url
    }
