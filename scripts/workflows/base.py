"""Workflow base classes and infrastructure."""

import sys
import time
from dataclasses import dataclass, field


@dataclass
class WorkflowResult:
    """Universal workflow output container."""
    workflow: str
    status: str                          # "complete" | "partial" | "failed"
    data: dict = field(default_factory=dict)
    markdown: str = ""
    blueprint_spec: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class WorkflowAbort(Exception):
    """Raised when error_policy='abort' and a step fails."""
    pass


class RateLimiter:
    """Simple inter-request delay to avoid API rate limits."""

    def __init__(self, requests_per_second: float = 2.0):
        self._min_interval = 1.0 / requests_per_second
        self._last_call = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()


class WorkflowRunner:
    """Base class for all analysis workflows."""

    NAME = ""
    DESCRIPTION = ""

    def __init__(self, api_key: str, platform: str, error_policy: str = "continue"):
        self.api_key = api_key
        self.platform = platform
        self.error_policy = error_policy
        self.adapter = self._get_adapter(platform, api_key)
        self._rate_limiter = RateLimiter(requests_per_second=1.5)
        self._errors: list[dict] = []
        self._api_calls = 0

    def _get_adapter(self, platform: str, api_key: str):
        """Instantiate the platform adapter."""
        _script_dir = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
        _platforms_dir = __import__("os").path.join(__import__("os").path.dirname(_script_dir), "platforms")
        if _platforms_dir not in sys.path:
            sys.path.insert(0, __import__("os").path.dirname(_script_dir))

        from platforms import ADAPTERS
        adapter_cls = ADAPTERS.get(platform)
        if not adapter_cls:
            raise ValueError(f"Unknown platform: {platform}. Available: {', '.join(ADAPTERS.keys())}")
        return adapter_cls(api_key)

    def run(self, **kwargs) -> WorkflowResult:
        """Execute the workflow and return a WorkflowResult."""
        start = time.time()
        try:
            data = self._execute(**kwargs)
        except WorkflowAbort as e:
            return WorkflowResult(
                workflow=self.NAME, status="failed",
                markdown=f"❌ Workflow aborted: {e}",
                errors=self._errors,
                metadata={"elapsed_seconds": time.time() - start, "api_calls": self._api_calls, "platform": self.platform},
            )

        elapsed = time.time() - start
        markdown = self._format_markdown(data)
        blueprint = self._build_blueprint_spec(data)

        return WorkflowResult(
            workflow=self.NAME,
            status="partial" if self._errors else "complete",
            data=data,
            markdown=markdown,
            blueprint_spec=blueprint,
            errors=self._errors,
            metadata={"elapsed_seconds": round(elapsed, 1), "api_calls": self._api_calls, "platform": self.platform},
        )

    def _execute(self, **kwargs) -> dict:
        raise NotImplementedError

    def _format_markdown(self, data: dict) -> str:
        raise NotImplementedError

    def _build_blueprint_spec(self, data: dict) -> dict:
        return {}

    def _safe_call(self, step_name: str, fn, *args, **kwargs):
        """Call an adapter method with rate limiting and error handling."""
        self._rate_limiter.wait()
        self._api_calls += 1
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception as e:
            self._errors.append({"step": step_name, "error": str(e)})
            if self.error_policy == "abort":
                raise WorkflowAbort(f"Step '{step_name}' failed: {e}")
            return None

    def _progress(self, msg: str):
        """Print progress message to stderr."""
        print(f"  {msg}", file=sys.stderr, flush=True)
