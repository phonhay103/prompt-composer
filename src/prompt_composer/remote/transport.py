"""Default HTTP transport implementation using standard library urllib."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, override

from prompt_composer.remote.base import RemoteTransport


class UrllibRemoteTransport(RemoteTransport):
    """Default HTTP transport using standard library urllib."""

    @override
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an HTTP request and return the parsed JSON response."""
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL scheme must be http or https, got: {url}")

        req_headers = dict(headers) if headers else {}
        if params:
            # Filter out None values from params
            filtered_params = {k: str(v) for k, v in params.items() if v is not None}
            if filtered_params:
                query_string = urllib.parse.urlencode(filtered_params)
                url = f"{url}?{query_string}"

        data = None
        if json_data is not None:
            data = json.dumps(json_data).encode("utf-8")
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)  # noqa: S310
        try:
            with urllib.request.urlopen(req) as response:  # noqa: S310
                resp_data = response.read().decode("utf-8")
                if not resp_data.strip():
                    return {}
                return json.loads(resp_data)
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                error_body = ""
            raise RuntimeError(
                f"HTTP request to {url} failed with status {e.code}: {e.reason}. Response: {error_body}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"HTTP request to {url} failed: {e}") from e
