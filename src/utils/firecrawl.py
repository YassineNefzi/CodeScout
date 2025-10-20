from firecrawl import FirecrawlApp

from ..config.settings import get_settings
from ..config.logging import Logger


class FirecrawlService:
    def __init__(self):
        self.settings = get_settings()
        self.logger = Logger().get_logger(name=self.__class__.__name__)

        api_key = self.settings.FIRECRAWL_API_KEY

        if not api_key:
            raise ValueError("Missing FIRECRAWL_API_KEY")

        self.app = FirecrawlApp(api_key=api_key)

    def search_companies(self, query: str, num_results: int = 5):
        try:
            result = self.app.search(
                query=f"{query} company pricing",
                limit=num_results,
                scrape_options={
                    "formats": ["markdown"]
                }
            )
            return result
        except Exception as e:
            self.logger.exception(e)
            return []

    def scrape_company_page(self, url: str):
        try:
            result = self.app.scrape(
                url=url,
                formats=["markdown"]
            )
            return result
        except Exception as e:
            self.logger.exception(e)
            return None