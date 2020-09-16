"""Base searcher class with helper attributes and methods for searchers."""
import abc
import logging
import os
from typing import Any, Dict

import cachetools
import github
import ircstyle
import pandas as pd

from .. import config

log = logging.getLogger(__name__)


class BaseSearcher(abc.ABC):
    """Base searcher class with helper attributes and methods for searchers."""

    def __init__(self, name: str):
        self.name = name
        self._github = github.Github(os.environ["GITHUB_TOKEN"].strip())
        self._github_user = self._github.get_user()
        log.info(f"Initalizing {self.name} searcher.")

    def __str__(self) -> str:
        return f"{self.name} searcher"

    @staticmethod
    def _process_results_df(df: pd.DataFrame) -> None:
        df.sort_values(by=["datetime"], ascending=False, inplace=True, ignore_index=True)
        df.drop_duplicates(subset=["channel", "feed", "long_url"], inplace=True, ignore_index=True)

    @abc.abstractmethod
    def _search(self, query: str) -> Dict[str, Any]:
        pass

    @property
    @abc.abstractmethod
    def _syntax_help(self) -> str:
        pass

    @cachetools.func.ttl_cache(maxsize=config.SEARCH_CACHE_MAXSIZE, ttl=config.SEARCH_CACHE_TTL)
    def search(self, query: str) -> str:
        """Return a summary containing a Gist link to the search results for the given query."""
        styled_name = ircstyle.style(self.name, italics=True, reset=True)
        response = self._search(query)
        df = response["results"]
        if df is None:  # Note: Explicit check prevents: ValueError: The truth value of a DataFrame is ambiguous
            styled_query = ircstyle.style(query, italics=True, reset=True)
            response_ = f"0 {styled_name} search results for {styled_query}. Refer to {self._syntax_help}"
            return response_

        markdown_df = df.copy()
        markdown_df.insert(0, "date_utc", markdown_df["datetime"].dt.date)
        markdown_df["title"] = "[" + markdown_df["title"].str.replace("|", r"\|") + "](" + markdown_df["long_url"] + ")"
        markdown_df.drop(columns=["datetime", "long_url", "short_url"], inplace=True)

        truncation_indicator = "max" if response["truncated"] else "all"
        gist = self._github_user.create_gist(
            public=False,
            files={
                "results.md": github.InputFileContent(markdown_df.to_markdown(index=False, tablefmt="github")),
                "results.csv": github.InputFileContent(df.to_csv(index=False)),
            },
            description=f"{query}: {truncation_indicator} {len(df)} search results from {self.name}",
        )

        styled_query = ircstyle.style(query, italics=True, reset=False)
        response = f"{truncation_indicator.capitalize()} {len(df)} search results → {gist.html_url}#file-results-md (from {styled_name} for {styled_query})"
        return response
