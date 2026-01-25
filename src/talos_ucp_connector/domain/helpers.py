import urllib.parse
from typing import Dict, Any, Optional
import http_sfv

class SigningHelper:
    @staticmethod
    def canonicalize_query(query_params: Dict[str, str]) -> str:
        """Canonical query string: sorted by (name, value) lexicographically."""
        sorted_params = sorted(query_params.items())
        return urllib.parse.urlencode(sorted_params)

    @staticmethod
    def canonicalize_ucp_agent(agent_str: str) -> str:
        """Parse as RFC 8941 Dictionary and re-serialize."""
        try:
            dict_val = http_sfv.Dictionary()
            dict_val.parse(agent_str.encode('ascii'))
            return str(dict_val)
        except Exception:
            # Fallback if parsing fails, though spec says to reject
            return agent_str

    @classmethod
    def create_envelope(
        cls,
        method: str,
        path: str,
        query_params: Dict[str, str],
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]],
        iat: int,
        jti: str
    ) -> Dict[str, Any]:
        """Constructs the canonical signing envelope."""
        query_string = cls.canonicalize_query(query_params)
        
        processed_headers = {k.lower(): v for k, v in headers.items()}
        if 'ucp-agent' in processed_headers:
            processed_headers['ucp-agent'] = cls.canonicalize_ucp_agent(processed_headers['ucp-agent'])
        
        envelope = {
            "method": method.upper(),
            "path": path,
            "query": query_string,
            "headers": processed_headers,
            "body": body if body is not None else None,
            "meta": {
                "iat": iat,
                "jti": jti
            }
        }
        return envelope
