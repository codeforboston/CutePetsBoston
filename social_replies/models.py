from dataclasses import dataclass, field
from typing import Protocol

from abstractions import PostResult
from database import PublishedPost


@dataclass
class Comment:
    platform: str
    comment_id: str
    root_id: str
    author_id: str
    author: str
    text: str
    created_at: str
    url: str = ""
    is_own: bool = False
    is_bot: bool = False
    answered: bool = False
    context: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.platform}:{self.comment_id}"

    @property
    def thread_key(self) -> str:
        return f"{self.platform}:{self.root_id}"


class ReplyAdapter(Protocol):
    platform_name: str

    def read(self, post: PublishedPost) -> list[Comment]: ...

    def reply(self, comment: Comment, text: str) -> PostResult: ...
