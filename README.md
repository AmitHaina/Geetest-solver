# Geetest v4 Solver

A Geetest v4 captcha solver with support for slides, concurrency rate limiting, proof-of-work parallelization, and browser-emulated session caching.

## Features
- **Browser Emulation**: Uses [`horaa-tls`](https://github.com/AmitHaina/horaa-tls) to match Chrome headers, TLS fingerprints, and HTTP/2 settings.
- **Multiprocessing PoW**: Brute-forces challenge nonces in parallel.
- **Session Caching**: Thread-local session reuse with a configurable TTL to prevent stale connections.
- **Rate Limiting**: Concurrency queue limits and sliding-window IP rate limiting.

## CLI Usage
Start the solver API:
```bash
python api_solver.py --host 0.0.0.0 --port 5000 --threads 4 --queue-limit 4 --ip-rate-limit-max 5 --ip-rate-limit-window 60
```

Solve via command line:
```bash
python -m gtv4 <captcha_id> <risk_type> [proxy]
```

## Python Usage (Client Request to API)
```python
import requests

response = requests.post(
    "http://127.0.0.1:5000/geetest",
    json={
        "captcha_id": "54088bb07d2df3c46b79f80300b0abbe",
        "risk_type": "slide",
        "proxy": "http://127.0.0.1:8080"
    }
).json()

print("Solved seccode:", response.get("solution"))
```

## Contributing
Contributors are welcome. Feel free to open a pull request for any improvements or create an issue for any errors.

## Community
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/QphWRKHvH2)
