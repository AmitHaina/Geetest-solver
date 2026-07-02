# Geetest v4 Solver

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/QphWRKHvH2)

A request-based Geetest v4 captcha solver in Python. This library interacts with Geetest endpoints directly and solves challenges locally, bypassing the need for a web browser or automated driver (such as Selenium, Playwright, or Puppeteer).

## Features

* **No Web Browser Required**: Solves challenges directly via HTTP requests.
* **Slide Solver**: Automatically detects gaps using OpenCV Canny edge detection and template matching.
* **JA3/TLS Emulation**: Uses [horaa-tls](https://github.com/AmitHaina/horaa-tls) to match browser TLS and HTTP/2 fingerprints.
* **HTTP API Server**: Includes a Flask-based API server that mirrors standard Turnstile/Geetest captcha APIs.

## Requirements

* Python 3.10 or higher
* OpenCV
* NumPy
* Flask
* PyCryptodome
* horaa-tls

Install dependencies:

```bash
pip install -r requirements.txt
```

## Python Library Usage

Here is how to import the solver and run a solve session in a Python script or interactive shell:

```python
import gtv4.solver

# Execute a solve for a slide challenge
solution = gtv4.solver.solve(
    captcha_id="54088bb07d2df3c46b79f80300b0abbe",
    risk_type="slide"
)

# Output the solved seccode details
print(solution)
```

## Command Line Interface

You can run the solver directly from the terminal. 

To run the built-in demo slide challenge:

```bash
python -m gtv4
```

To run with custom parameters:

```bash
python -m gtv4 <captcha_id> <risk_type> [proxy]
```

Example:

```bash
python -m gtv4 54088bb07d2df3c46b79f80300b0abbe slide http://127.0.0.1:8080
```

## HTTP API Server

The project includes a Flask-based HTTP API server in `api_solver.py` for serving solve requests.

### Start the Server

```bash
python api_solver.py --host 0.0.0.0 --port 5000 --threads 4
```

### Solve Request

Post a JSON request to the `/geetest` endpoint:

```bash
curl -X POST http://127.0.0.1:5000/geetest \
  -H "Content-Type: application/json" \
  -d '{
    "captcha_id": "54088bb07d2df3c46b79f80300b0abbe",
    "risk_type": "slide"
  }'
```

### Response Format

A successful solve returns the `seccode` object inside the `solution` key:

```json
{
  "errorId": 0,
  "status": "ready",
  "solution": {
    "captcha_id": "54088bb07d2df3c46b79f80300b0abbe",
    "lot_number": "lot_...",
    "pass_token": "pass_...",
    "gen_time": "1719999999",
    "captcha_output": "output_..."
  }
}
```

If the solve fails or times out, the server returns an error code:

```json
{
  "errorId": 1,
  "errorCode": "ERROR_CAPTCHA_UNSOLVABLE",
  "errorDescription": "failed to decode slide images"
}
```

## Contributing

Pull requests are welcome. If you open one, please describe your changes properly in the PR description so it's clear what you changed and why.

## Contact

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/QphWRKHvH2)
