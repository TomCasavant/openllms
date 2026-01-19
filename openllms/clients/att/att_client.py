from openllms.clients.att import ATTResponse
from openllms.models.llm import LLM


class ATTClient(LLM):
    name = "att"

    BASE_URL = "https://services.att.com/search/v2/answerextraction"

    async def query(
        self,
        search_term: str,
        app_id: str = "idpSupport", # Unclear if there are other apps to hit, this seems to be the llm search one
        include_datasources: str = "search", # Unsure of other options for this?
        is_related_qna_enabled: bool = True,
        is_call_llm: bool = True, # When set to false, does not call the LLM, not sure why you would want that?
        gpt_version: str = "gpt-4o", # Changing this doesn't seem to impact the result, though I may have been missing something?
        genai_click: bool = True, # No idea what this does
        call_spectra: bool = True, # No idea what this does
        navigation_tree: str = '"~Support~","~Support~All~"', # Seemed to be the default, not sure how this impacts AI response
        source_page: str = "/support/contact-us/", # Seemed to be the default
        response_signal: bool = True, # Unclear what False does to this
    ) -> ATTResponse:
        prompt = self.build_prompt(search_term)

        params = {
            "app-id": app_id,
            "includeDatasources": include_datasources,
            "isRelatedQnAEnabled": str(is_related_qna_enabled).lower(),
            "isCallLLM": str(is_call_llm).lower(),
            "gptVersion": gpt_version,
            "genAIclick": str(genai_click).lower(),
            "callSpectra": str(call_spectra).lower(),
            "navigationTree": navigation_tree,
            "sourcePage": source_page,
            "searchTerm": prompt,
            "responseSignal": str(response_signal).lower(),
        }

        data = await self._get(self.BASE_URL, params=params)

        return ATTResponse.from_raw(data)