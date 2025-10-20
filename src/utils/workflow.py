from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from ..config.logging import Logger
from ..config.schemas import ResearchState, CompanyInfo, CompanyAnalysis
from ..config.prompts import DeveloperToolsPrompts
from .firecrawl import FirecrawlService
from .llm import GroqLLM


class Workflow:
    def __init__(self):
        self.logger = Logger().get_logger(name=self.__class__.__name__)
        self.firecrawl = FirecrawlService()
        self.llm = GroqLLM().get_llm()
        self.prompts = DeveloperToolsPrompts()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        graph = StateGraph(ResearchState)
        graph.add_node("extract_tools", self._extract_tools_step)
        graph.add_node("research", self._research_step)
        graph.add_node("analyze", self._analyze_step)
        graph.set_entry_point("extract_tools")
        graph.add_edge("extract_tools", "research")
        graph.add_edge("research", "analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    def _extract_tools_step(self, state: ResearchState) -> Dict[str, Any]:
        self.logger.info(f"🔍 Finding articles about: {state.query}")

        article_query = f"{state.query} tools comparison best alternatives"
        search_results = self.firecrawl.search_companies(article_query, num_results=3)

        # Handle both empty list (error case) and SearchData object
        if not search_results or isinstance(search_results, list):
            self.logger.warning("No search results found")
            return {"extracted_tools": []}

        # Access results - check what attribute the SearchData object has
        results = getattr(search_results, 'results', getattr(search_results, 'data', []))

        all_content = ""
        for result in results:
            url = result.get("url", "")
            scraped = self.firecrawl.scrape_company_page(url)
            if scraped:
                # Fixed: was missing assignment operator
                all_content += scraped.markdown[:1500] + "\n\n"

        messages = [
            SystemMessage(content=self.prompts.TOOL_EXTRACTION_SYSTEM),
            HumanMessage(content=self.prompts.tool_extraction_user(state.query, all_content))
        ]

        try:
            response = self.llm.invoke(messages)
            tool_names = [
                name.strip()
                for name in response.content.strip().split("\n")
                if name.strip()
            ]
            print(f"Extracted tools: {', '.join(tool_names[:5])}")
            return {"extracted_tools": tool_names}
        except Exception as e:
            self.logger.exception(f"Error extracting tools: {e}")
            return {"extracted_tools": []}

    def _analyze_company_content(self, company_name: str, content: str) -> CompanyAnalysis:
        structured_llm = self.llm.with_structured_output(CompanyAnalysis)

        messages = [
            SystemMessage(content=self.prompts.TOOL_ANALYSIS_SYSTEM),
            HumanMessage(content=self.prompts.tool_analysis_user(company_name, content))
        ]

        try:
            analysis = structured_llm.invoke(messages)
            return analysis
        except Exception as e:
            self.logger.exception(f"Error analyzing company: {e}")
            return CompanyAnalysis(
                pricing_model="Unknown",
                is_open_source=None,
                tech_stack=[],
                description="Failed",
                api_available=None,
                language_support=[],
                integration_capabilities=[],
            )

    def _research_step(self, state: ResearchState) -> Dict[str, Any]:
        extracted_tools = getattr(state, "extracted_tools", [])

        if not extracted_tools:
            self.logger.warning("⚠️ No extracted tools found, falling back to direct search")
            search_results = self.firecrawl.search_companies(state.query, num_results=4)

            # Handle both empty list and SearchData object
            if not search_results or isinstance(search_results, list):
                self.logger.error("No search results in fallback")
                return {"companies": []}

            results = getattr(search_results, 'results', getattr(search_results, 'data', []))
            tool_names = [
                result.get("metadata", {}).get("title", "Unknown")
                for result in results
            ]
        else:
            tool_names = extracted_tools[:4]

        self.logger.info(f"🔬 Researching specific tools: {', '.join(tool_names)}")

        companies = []
        for tool_name in tool_names:
            tool_search_results = self.firecrawl.search_companies(tool_name + " official site", num_results=1)

            # Handle empty results
            if not tool_search_results or isinstance(tool_search_results, list):
                continue

            results = getattr(tool_search_results, 'results', getattr(tool_search_results, 'data', []))

            if results:
                result = results[0]
                url = result.get("url", "")

                company = CompanyInfo(
                    name=tool_name,
                    description=result.get("markdown", ""),
                    website=url,
                    tech_stack=[],
                    competitors=[]
                )

                scraped = self.firecrawl.scrape_company_page(url)
                if scraped:
                    content = scraped.markdown
                    analysis = self._analyze_company_content(company.name, content)

                    company.pricing_model = analysis.pricing_model
                    company.is_open_source = analysis.is_open_source
                    company.tech_stack = analysis.tech_stack
                    company.description = analysis.description
                    company.api_available = analysis.api_available
                    company.language_support = analysis.language_support
                    company.integration_capabilities = analysis.integration_capabilities

                companies.append(company)

        return {"companies": companies}

    def _analyze_step(self, state: ResearchState) -> Dict[str, Any]:
        self.logger.info("Generating recommendations")

        company_data = ", ".join([
            company.model_dump_json() for company in state.companies
        ])

        messages = [
            SystemMessage(content=self.prompts.RECOMMENDATIONS_SYSTEM),
            HumanMessage(content=self.prompts.recommendations_user(state.query, company_data))
        ]

        response = self.llm.invoke(messages)
        return {"analysis": response.content}

    def run(self, query: str) -> ResearchState:
        initial_state = ResearchState(query=query)
        final_state = self.workflow.invoke(initial_state)
        return ResearchState(**final_state)