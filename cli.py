#!/usr/bin/env python3
"""
CLI entry point for the Binance USDT-M Futures Testnet trading bot.

Usage examples:

    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 120000

Run `python cli.py --help` for full usage.
"""

from __future__ import annotations

import argparse
import sys

from bot.client import BinanceFuturesClient
from bot.config import load_settings
from bot.exceptions import (
    AuthenticationError,
    BinanceAPIError,
    ConfigurationError,
    NetworkError,
    TradingBotError,
    ValidationError,
)
from bot.logging_config import setup_logging
from bot.orders import OrderResult, OrderService
from bot.validators import OrderRequest, build_order_request

SEPARATOR = "-" * 34


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct the argparse CLI parser with helpful descriptions and examples."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Place MARKET or LIMIT orders on the Binance USDT-M Futures Testnet.",
        epilog=(
            "Examples:\n"
            "  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01\n"
            "  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 120000\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--symbol", required=True, metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT",
    )
    parser.add_argument(
        "--side", required=True, choices=["BUY", "SELL", "buy", "sell"], metavar="SIDE",
        help="Order side: BUY or SELL",
    )
    parser.add_argument(
        "--type", required=True, dest="order_type",
        choices=["MARKET", "LIMIT", "market", "limit"], metavar="TYPE",
        help="Order type: MARKET or LIMIT",
    )
    parser.add_argument(
        "--quantity", required=True, type=str, metavar="QTY",
        help="Order quantity, e.g. 0.01",
    )
    parser.add_argument(
        "--price", required=False, default=None, type=str, metavar="PRICE",
        help="Limit price. Required for LIMIT orders, not allowed for MARKET orders.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose (DEBUG-level) console logging.",
    )
    parser.add_argument(
        "--env-file", default=None, metavar="PATH",
        help="Path to a .env file (defaults to .env in the current directory).",
    )

    return parser


def print_order_summary(order: OrderRequest) -> None:
    """Print a clean, pre-flight summary of the order about to be placed."""
    print(SEPARATOR)
    print("Order Summary")
    print(SEPARATOR)
    print(f"Symbol : {order.symbol}")
    print(f"Side   : {order.side.value}")
    print(f"Type   : {order.order_type.value}")
    print(f"Qty    : {order.quantity}")
    if order.price is not None:
        print(f"Price  : {order.price}")
    print(SEPARATOR)


def print_order_result(result: OrderResult) -> None:
    """Print the normalized order result returned by Binance."""
    print()
    print(f"Order ID          : {result.order_id}")
    print(f"Status            : {result.status}")
    print(f"Executed Quantity : {result.executed_qty}")
    print(f"Average Price     : {result.avg_price if result.avg_price else 'N/A (not yet filled)'}")
    print(f"Time              : {result.transact_time}")
    print()


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns:
        Process exit code: 0 on success, 1 on any handled failure.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logger = setup_logging(verbose=args.verbose)

    try:
        order = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
    except ValidationError as exc:
        print(f"✗ Invalid input: {exc}", file=sys.stderr)
        logger.warning("CLI validation failed: %s", exc)
        return 1

    print_order_summary(order)

    try:
        settings = load_settings(env_file=args.env_file)
        client = BinanceFuturesClient(settings)
        service = OrderService(client)
        result = service.place_order(order)
    except ConfigurationError as exc:
        print(f"✗ Configuration error: {exc}", file=sys.stderr)
        logger.error("Configuration error: %s", exc)
        return 1
    except AuthenticationError as exc:
        print(f"✗ Authentication failed: {exc}", file=sys.stderr)
        logger.error("Authentication error: %s", exc)
        return 1
    except NetworkError as exc:
        print(f"✗ Network error: {exc}", file=sys.stderr)
        logger.error("Network error: %s", exc)
        return 1
    except BinanceAPIError as exc:
        print(f"✗ Order failed: {exc}", file=sys.stderr)
        logger.error("Binance API error: %s", exc)
        return 1
    except TradingBotError as exc:
        print(f"✗ Order failed: {exc}", file=sys.stderr)
        logger.error("Unhandled trading bot error: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        print(f"✗ Unexpected error: {exc}", file=sys.stderr)
        logger.exception("Unexpected exception while placing order")
        return 1

    print_order_result(result)

    if result.status in {"NEW", "FILLED", "PARTIALLY_FILLED"}:
        print("✓ Order placed successfully")
        return 0

    print("✗ Order failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
