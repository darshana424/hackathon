class CrawlGraph:
    """
    Stores relationships between pages during crawl.
    """

    def __init__(self):
        self.outgoing = {}
        self.incoming = {}

    def add_page(self, url):
        if url not in self.outgoing:
            self.outgoing[url] = set()
        if url not in self.incoming:
            self.incoming[url] = set()

    def add_edge(self, source, target):
        self.add_page(source)
        self.add_page(target)

        self.outgoing[source].add(target)
        self.incoming[target].add(source)

    def get_outgoing(self, url):
        return self.outgoing.get(url, set())

    def get_incoming(self, url):
        return self.incoming.get(url, set())

    def orphan_pages(self):
        return [url for url, links in self.incoming.items() if not links]

    def pages(self):
        return list(self.outgoing.keys())
