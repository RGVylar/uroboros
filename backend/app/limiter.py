from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """Real client IP for rate limiting and abuse alerts.

    The backend runs behind Cloudflare Tunnel + Caddy, so request.client.host is
    always the proxy's internal address (e.g. 192.168.1.153) — identical for every
    external user. Cloudflare injects the true client IP in CF-Connecting-IP, which
    is what we key on so limits are per-user instead of global.
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, default_limits=[])
