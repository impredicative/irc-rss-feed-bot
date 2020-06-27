import logging
import os
import urllib

import github
from descriptors import cachedproperty

from ircrssfeedbot import config

from . import BaseChannelPublisher

log = logging.getLogger(__name__)


class ChannelPublisher(BaseChannelPublisher):
    """Get and set content for channel.

    An instance of this class should be used from a single thread only, and is otherwise not thread-safe.
    """

    def __init__(self, channel: str):
        super(ChannelPublisher, self).__init__(channel)
        self._repo = github.Github(os.getenv("GITHUB_TOKEN")).get_repo(self.repo)
        self._init_content_and_sha()

    def _init_content_and_sha(self) -> None:
        content_desc = f"content file for {self.channel} on GitHub"
        try:
            log.debug("Attempting to read existing %s.", content_desc)
            content_file = self._repo.get_contents(path=self.channel_path)
            log.debug("Read existing %s.", content_desc)
        except github.GithubException.UnknownObjectException:
            log.debug("Unable to read existing %s.", content_desc)
            log.debug("Creating new %s.", content_desc)
            content_file = self._repo.create_file(path=self.channel_path, message=f"Initialize RSS content for {self.channel}", content=self.default_content,)["content"]
            log.info("Created new %s.", content_desc)
        self._content, self._sha = content_file.decoded_content(), content_file.sha

    @cachedproperty
    def channel_url(self) -> str:
        quoted_repo = urllib.parse.quote(self.repo)
        quoted_channel_path = urllib.parse.quote(self.channel_path)
        return f"https://raw.githubusercontent.com/{quoted_repo}/master/{quoted_channel_path}"

    @property
    def content(self) -> bytes:
        return self._content

    @content.setter
    def content(self, xml: bytes) -> None:
        content_desc = f"content file for {self.channel} on GitHub"
        log.debug("Updating existing %s.", content_desc)
        content_file = self._repo.update_file(path=self.channel, message=f"Update RSS content for {self.channel}", content=xml)["content"]
        log.info("Updated existing %s.", content_desc)
        self._content, self._sha = content_file.decoded_content(), content_file.sha

    @cachedproperty
    def repo_url(self) -> str:
        quoted_repo = urllib.parse.quote(self.repo)
        return f"https://github.com/{quoted_repo}"
