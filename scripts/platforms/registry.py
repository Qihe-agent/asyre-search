"""Endpoint registry — loads api_registry.json + action_map.json and resolves endpoints."""

import json
import os
from dataclasses import dataclass, field


@dataclass
class EndpointSpec:
    """Resolved endpoint specification."""
    method: str                        # "GET" or "POST"
    path: str                          # "/api/v1/douyin/app/v3/fetch_one_video"
    summary: str = ""
    category: str = ""
    params: dict = field(default_factory=dict)   # query param schema
    body: dict | None = None           # POST body schema
    deprecated: bool = False
    version: str | None = None
    recommended: bool = False


class EndpointRegistry:
    """Loads and resolves API endpoints from the generated registry."""

    def __init__(self, registry_dir: str = None):
        if registry_dir is None:
            # Default: PROJECT_ROOT/registry/
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(os.path.dirname(script_dir))
            registry_dir = os.path.join(project_dir, "registry")

        self._registry_dir = registry_dir
        self._platforms = {}
        self._action_map = {}
        self._path_index = {}  # path -> EndpointSpec for direct lookup

        self._load(registry_dir)

    def _load(self, registry_dir: str):
        """Load registry and action map from JSON files."""
        reg_path = os.path.join(registry_dir, "api_registry.json")
        map_path = os.path.join(registry_dir, "action_map.json")

        if not os.path.exists(reg_path):
            raise FileNotFoundError(
                f"Registry not found: {reg_path}\n"
                f"Run: python3 scripts/generate_registry.py"
            )

        with open(reg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._platforms = data.get("platforms", {})

        # Build path index
        for plat_data in self._platforms.values():
            for mod_data in plat_data.get("modules", {}).values():
                for ep_name, ep in mod_data.get("endpoints", {}).items():
                    spec = self._to_spec(ep)
                    self._path_index[ep["path"]] = spec

        # Load action map (optional — tool works without it via raw)
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Strip _comment key
            self._action_map = {k: v for k, v in raw.items() if not k.startswith("_")}

    @staticmethod
    def _to_spec(ep: dict) -> EndpointSpec:
        """Convert raw endpoint dict to EndpointSpec."""
        return EndpointSpec(
            method=ep.get("method", "GET"),
            path=ep.get("path", ""),
            summary=ep.get("summary", ""),
            category=ep.get("category", ""),
            params=ep.get("params", {}),
            body=ep.get("body"),
            deprecated=ep.get("deprecated", False),
            version=ep.get("version"),
            recommended=ep.get("recommended", False),
        )

    # ── Resolution ───────────────────────────────────────────────

    def resolve(self, platform: str, action: str, variant: str = None) -> EndpointSpec:
        """Resolve (platform, action) → EndpointSpec.

        Args:
            platform: e.g. "douyin", "xiaohongshu"
            action: e.g. "info", "user", "posts", "search", "trending", "comments"
            variant: optional sub-key, e.g. "by_url", "by_id"

        Returns:
            EndpointSpec with method, path, params, body, etc.

        Raises:
            KeyError if platform/action not found in action_map.
        """
        plat_map = self._action_map.get(platform)
        if not plat_map:
            raise KeyError(f"Platform '{platform}' not in action_map")

        mapping = plat_map.get(action)
        if mapping is None:
            raise KeyError(f"Action '{action}' not mapped for platform '{platform}'")

        # Mapping can be a string "module/endpoint" or a dict of variants
        if isinstance(mapping, dict):
            if variant:
                ref = mapping.get(variant)
                if not ref:
                    raise KeyError(f"Variant '{variant}' not found for {platform}/{action}")
            else:
                # Pick first variant as default
                ref = next(iter(mapping.values()))
        else:
            ref = mapping

        # ref is "module_key/endpoint_name"
        return self._resolve_ref(platform, ref)

    def _resolve_ref(self, platform: str, ref: str) -> EndpointSpec:
        """Resolve a 'module/endpoint_name' reference to EndpointSpec."""
        parts = ref.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid endpoint ref: '{ref}' (expected 'module/endpoint_name')")

        module_key, ep_name = parts
        plat_data = self._platforms.get(platform, {})
        mod_data = plat_data.get("modules", {}).get(module_key, {})
        ep = mod_data.get("endpoints", {}).get(ep_name)

        if not ep:
            raise KeyError(f"Endpoint not found: {platform}/{module_key}/{ep_name}")

        return self._to_spec(ep)

    def lookup(self, path: str) -> EndpointSpec | None:
        """Direct lookup by full API path (for `raw` command)."""
        return self._path_index.get(path)

    # ── Discovery ────────────────────────────────────────────────

    def list_platforms(self) -> list[str]:
        """List all platforms in the registry."""
        return sorted(self._platforms.keys())

    def list_actions(self, platform: str) -> list[str]:
        """List available actions for a platform (from action_map)."""
        return sorted(self._action_map.get(platform, {}).keys())

    def search_endpoints(self, query: str, platform: str = None) -> list[EndpointSpec]:
        """Search endpoints by keyword in summary or path."""
        query_lower = query.lower()
        results = []

        platforms = {platform: self._platforms[platform]} if platform and platform in self._platforms else self._platforms

        for plat_data in platforms.values():
            for mod_data in plat_data.get("modules", {}).values():
                for ep in mod_data.get("endpoints", {}).values():
                    if (query_lower in ep.get("summary", "").lower() or
                            query_lower in ep.get("path", "").lower()):
                        results.append(self._to_spec(ep))

        return results
