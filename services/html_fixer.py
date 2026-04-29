from bs4 import BeautifulSoup
import json


def apply_meta_update(html, title=None, description=None):

    soup = BeautifulSoup(html, "lxml")

    if title:
        title_tag = soup.find("title")
        if title_tag:
            title_tag.string = title

    if description:
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta["content"] = description

    return str(soup)


def inject_schema(html, schema):

    soup = BeautifulSoup(html, "lxml")

    script = soup.new_tag("script", type="application/ld+json")
    script.string = json.dumps(schema)

    if soup.head:
        soup.head.append(script)

    return str(soup)
