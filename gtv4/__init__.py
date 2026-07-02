"""
gtv4 — a Geetest v4 captcha solver.

Request-based: talks to the Geetest endpoints directly and reconstructs the
challenge response locally, without driving a real browser.
"""

import logging

# Library convention: attach a no-op handler so importing apps that don't
# configure logging don't get "No handlers" warnings. The app decides output.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__version__ = "0.1.0"
