from abc import ABC, abstractmethod
from typing import Any
import time

from ..models import AgentTrace


class BaseAgent(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    def record_trace(self, action: str, status: str, details: Any = None) -> AgentTrace:
        return AgentTrace(
            agent_id=self.name, action=action, status=status, timestamp=time.time(), details=details
        )

    @abstractmethod
    def run(self, context: Any, **kwargs: Any) -> Any:
        pass
