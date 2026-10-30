"""HTTPS tunnel entry point. The ordinary localhost server remains unchanged."""
import argparse
import re
from .app import create_app


def create_share_app(hostname):
    if not isinstance(hostname,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com',hostname):
        raise ValueError('Expected the exact hostname issued by Cloudflare Quick Tunnel.')
    return create_app({
        'TRUSTED_HOSTS':[hostname],
        'SESSION_COOKIE_NAME':'qazcargo_share_session',
        'SESSION_COOKIE_SECURE':True,
    })


if __name__=='__main__':
    from waitress import serve
    parser=argparse.ArgumentParser()
    parser.add_argument('--hostname',required=True)
    args=parser.parse_args()
    # This listener is only reachable on loopback; its only public ingress is
    # the HTTPS tunnel. Never trust browser-supplied forwarding headers.
    serve(create_share_app(args.hostname),host='127.0.0.1',port=5002,
          url_scheme='https',clear_untrusted_proxy_headers=True,threads=8,
          max_request_body_size=21*1024*1024)
