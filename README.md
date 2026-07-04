# Trading Bot — Binance USDT-M Futures Testnet

A small, production-style CLI application for placing **MARKET** and **LIMIT**
orders on the [Binance USDT-M Futures Testnet](https://testnet.binancefuture.com).

Built to demonstrate clean architecture, robust validation, structured
logging, and proper error handling rather than a "just make the API call"
script.

---

## Features

- Place **MARKET** and **LIMIT** orders, **BUY** or **SELL**, on USDT-M Futures.
- Argparse-based CLI with clear `--help`, strict input validation, and
  friendly error messages.
- Clean separation of concerns:
  - `bot/validators.py` — pure input validation, no network/IO.
  - `bot/client.py` — signed REST client (HMAC-SHA256, retries, timeouts).
  - `bot/orders.py` — business logic that turns a request into an API call
    and a response into a normalized result.
  - `bot/config.py` — environment-based configuration via `.env`.
  - `bot/logging_config.py` — rotating file + console logging with secret
    redaction.
  - `cli.py` — thin CLI layer; contains no business logic.
- Rotating log files (`logs/trading_bot.log`, 5 MB × 5 backups) capturing
  every request, response, and error — **without ever logging your API
  secret**.
- Graceful handling of invalid input, authentication failures, network
  errors, and unexpected exceptions — the CLI always exits with a clear
  message and a non-zero exit code on failure.
- Unit tests for the validation layer (`tests/test_validators.py`).

---

## Folder Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py           # Signed REST client for Binance Futures API
│   ├── orders.py           # Order building + response normalization
│   ├── validators.py       # Input validation, OrderRequest dataclass
│   ├── config.py           # .env loading, Settings dataclass
│   ├── exceptions.py       # Custom exception hierarchy
│   └── logging_config.py   # Rotating file logger + secret redaction
├── logs/                   # Rotating log files (created automatically)
├── tests/
│   └── test_validators.py
├── .env.example
├── .gitignore
├── cli.py                  # CLI entry point
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Clone / unzip the project

```bash
cd trading_bot
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

1. Register for a [Binance Futures Testnet](https://testnet.binancefuture.com)
   account and generate an API key/secret from the testnet dashboard.
2. Copy the example env file:

   ```bash
   cp .env.example .env
   ```

3. Fill in your credentials in `.env`:

   ```env
   BINANCE_API_KEY=your_testnet_api_key_here
   BINANCE_SECRET_KEY=your_testnet_secret_key_here
   BINANCE_BASE_URL=https://testnet.binancefuture.com
   ```

`.env` is git-ignored — your credentials never get committed.

---

## Running the Bot

### Market order example

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order example

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 120000
```

### Full CLI usage

```bash
python cli.py --help
```

```
usage: cli.py [-h] --symbol SYMBOL --side SIDE --type TYPE --quantity QTY
              [--price PRICE] [--verbose] [--env-file PATH]

Place MARKET or LIMIT orders on the Binance USDT-M Futures Testnet.

options:
  -h, --help          show this help message and exit
  --symbol SYMBOL     Trading pair symbol, e.g. BTCUSDT
  --side SIDE         Order side: BUY or SELL
  --type TYPE         Order type: MARKET or LIMIT
  --quantity QTY      Order quantity, e.g. 0.01
  --price PRICE       Limit price. Required for LIMIT orders, not allowed for MARKET orders.
  --verbose           Enable verbose (DEBUG-level) console logging.
  --env-file PATH     Path to a .env file (defaults to .env in the current directory).
```

### Sample output

```
----------------------------------
Order Summary
----------------------------------
Symbol : BTCUSDT
Side   : BUY
Type   : MARKET
Qty    : 0.01
----------------------------------

Order ID          : 123456789
Status            : NEW
Executed Quantity : 0.000
Average Price     : N/A (not yet filled)
Time              : 2026-07-03T10:15:00+00:00

✓ Order placed successfully
```

On failure:

```
✗ Order failed: Binance API error (code=-2019, http_status=400): Margin is insufficient.
```

---

## Validation Rules

The CLI validates input **before** any network call is made:

- `--symbol` must be a non-empty alphanumeric pair (e.g. `BTCUSDT`); it is
  normalized to uppercase.
- `--side` must be `BUY` or `SELL` (case-insensitive).
- `--type` must be `MARKET` or `LIMIT` (case-insensitive).
- `--quantity` must be a positive number.
- `--price` is **required** for `LIMIT` orders and **rejected** for
  `MARKET` orders (Binance MARKET orders always fill at best available
  price, so supplying a price is a validation error, not silently ignored).

---

## Logging

All activity is logged to `logs/trading_bot.log` using a rotating file
handler (5 MB per file, 5 backups retained). Each entry includes a
timestamp, log level, and message. Logged events include:

- Outgoing requests (method, endpoint, sanitized parameters)
- Incoming responses (status code, response body)
- Validation failures
- Authentication failures
- Network errors and retries
- Full exception stack traces for unexpected errors

**API keys and secrets are never written to the log file.** A dedicated
`SecretRedactingFilter` strips API keys, secrets, and request signatures
from any log line as defense in depth, in addition to the client never
passing secrets to the logger in the first place.

Run with `--verbose` to also see DEBUG-level detail on the console.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Configuration error: Missing BINANCE_API_KEY...` | `.env` missing or not filled in | Copy `.env.example` to `.env` and add your testnet keys |
| `Authentication failed` | Wrong/expired API key or secret | Regenerate keys on the testnet dashboard |
| `Network error: Failed to reach Binance...` | No internet access, firewall, or Binance testnet outage | Check connectivity; the client retries transient failures automatically |
| `Binance API error (code=-1121...)` | Invalid or unsupported symbol | Verify the symbol exists on USDT-M Futures Testnet |
| `Binance API error (code=-2019...)` | Insufficient testnet margin | Fund your testnet futures wallet from the testnet faucet |
| `✗ Invalid input: Price is required for LIMIT orders.` | Forgot `--price` on a LIMIT order | Add `--price <value>` |

---

## Assumptions

- Only USDT-M Futures MARKET and LIMIT orders are in scope (per the
  assignment); other order types (STOP, TAKE_PROFIT, etc.) are out of
  scope for the core requirement.
- LIMIT orders default to `timeInForce=GTC` (Good-Til-Canceled), the
  standard default and a required field for LIMIT orders on Binance.
- The bot targets the Futures **Testnet** exclusively; switching to
  production would only require changing `BINANCE_BASE_URL` (and using
  real, funded credentials) — no code changes needed.
- Quantity/price precision (`stepSize`/`tickSize` per symbol) is validated
  by Binance server-side; the client surfaces any resulting error message
  rather than duplicating exchange-info precision rules client-side.

---

## Future Improvements

- Fetch and cache `/fapi/v1/exchangeInfo` to validate symbol existence and
  quantity/price precision client-side before submitting.
- Add Stop-Limit and OCO order support.
- Add an interactive (Rich/Typer-based) menu mode alongside the flag-based CLI.
- Add integration tests using `responses`/`requests-mock` to simulate
  Binance API responses.
- Add async support (`httpx.AsyncClient`) for batch/parallel order placement.

---

## Testing

```bash
python -m unittest discover -s tests -v
```
