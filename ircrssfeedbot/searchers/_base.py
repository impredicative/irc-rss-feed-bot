"""Base searcher class with helper attributes and methods for searchers."""
import abc
import logging
import multiprocessing
import multiprocessing.pool
import os
from typing import List, Optional, TypedDict

import cachetools.func
import github
import ircstyle
import pandas as pd

from .. import config

log = logging.getLogger(__name__)


class SearchResults(TypedDict):
    """Dictionary of search results as returned by a searcher."""

    results: Optional[pd.DataFrame]
    truncated: Optional[bool]


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
    def _concat_results_dfs(dfs: List[pd.DataFrame]) -> None:
        df = pd.concat(dfs)
        dfs.clear()
        df.sort_values(by=["datetime"], ascending=False, inplace=True, ignore_index=True)
        df.drop_duplicates(subset=["channel", "feed", "long_url"], inplace=True, ignore_index=True)
        dfs.append(df)
        assert len(dfs) == 1

    @abc.abstractmethod
    def _search(self, query: str) -> SearchResults:
        pass

    @property
    @abc.abstractmethod
    def _syntax_help(self) -> str:
        pass

    @staticmethod
    def fix_query(query: str) -> str:
        """Return the fixed query, removing extra spaces."""
        return " ".join(query.split())

    def _search_inner(self, query: str) -> str:
        log.debug(f"Searching {self.name} for {query!r}.")
        styled_name = ircstyle.style(self.name, italics=True, reset=True)
        response = self._search(query)
        df = response["results"]
        if df is None:  # Note: Explicit check prevents: ValueError: The truth value of a DataFrame is ambiguous
            styled_query = ircstyle.style(query, italics=True, reset=True)
            response_ = f"0 {styled_name} search results for {styled_query}."
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

    @cachetools.func.ttl_cache(maxsize=config.SEARCH_CACHE_MAXSIZE, ttl=config.SEARCH_CACHE_TTL)  # type: ignore
    def search(self, query: str) -> str:
        """Return a summary containing a Gist link to the search results for the given query."""
        return self.worker_pool.apply(self._search_inner, (query,))  # To prevent accumulation of potential memory leaks.

    @property
    def worker_pool(self) -> multiprocessing.pool.Pool:
        # Ref: https://stackoverflow.com/a/63984747/
        # Note: This approach is used instead of a ClassVar because the latter led to errors when "spawning" worker processes.
        try:
            return self._worker_pool  # type: ignore
        except AttributeError:
            processes = 1
            maxtasksperchild = 4
            log.info(f"Creating the {self.__class__.__name__} worker pool with {processes} processes and {maxtasksperchild} tasks per child.")
            # pylint: disable=protected-access
            self.__class__._worker_pool = multiprocessing.Pool(processes=processes, maxtasksperchild=maxtasksperchild)  # type: ignore
            return self.__class__._worker_pool  # type: ignore
            # pylint: enable=protected-access
