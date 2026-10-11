from pydantic import BaseModel


class SyncTriggerIn(BaseModel):
    source: str  # github / leetcode / nowcoder
    mode: str = "incremental"  # full / incremental
