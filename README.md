# shopkit

A small e-commerce domain library in Python: products, a shopping cart, coupon codes and Swiss
VAT, with money handled as `Decimal` and explicit rounding. It also ships a small command line
tool that prints a priced quote for a cart file.

```console
$ python -m shopkit quote examples/cart.json --coupons examples/coupons.json --today 2026-10-01
  3 x Green tea, 100 g         CHF 14.70
  2 x Stoneware mug            CHF 36.00
  1 x The Art of Brewing       CHF 29.00
Subtotal                       CHF 79.70
Coupon WELCOME10               -CHF 7.97
VAT 8.1% (standard)             CHF 2.62
VAT 2.6% (reduced)              CHF 1.02
Total                          CHF 75.37
Total (cash)                   CHF 75.35
```

## Features

- **Products and cart:** net unit prices (excluding VAT), one line per SKU, quantities 1–999.
- **VAT:** the Swiss rates (8.1 % standard, 2.6 % reduced, 3.8 % accommodation, exempt) as plain
  configuration (`shopkit.vat.SWISS_RATES`); pass your own `VatRates` for other rates.
- **Coupons:** a percentage or a fixed amount off the net subtotal, with an optional last valid
  day and a minimum subtotal.
- **Money:** `Decimal` only; amounts round to the cent (half up), cash totals to 5 Rappen.

## Development

Requires Python 3.12 or newer. Development tools are pinned exactly in `requirements-dev.txt`
(this project uses a pip requirements file, not a lock file from another tool).

| Step | Command |
|---|---|
| Setup | `python -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements-dev.txt -e .` |
| Test | `pytest -q` |
| Lint | `ruff check . && ruff format --check .` |
| Type check | `mypy src` |

All four run in CI (`.github/workflows/ci.yml`) on every pull request and on pushes to `main`.
The tests need no network access and finish in a few seconds.

See [AGENTS.md](AGENTS.md) for the contribution conventions and [CHANGELOG.md](CHANGELOG.md)
for the release history.

## Cart file format

```json
{
  "lines": [
    {"sku": "TEA-GREEN", "name": "Green tea, 100 g", "unit_price": "4.90", "quantity": 3, "vat": "reduced"}
  ],
  "coupon": "WELCOME10"
}
```

Prices are strings so they are never parsed as floats. `vat` is one of `standard` (default),
`reduced`, `accommodation` or `exempt`. Coupons come from a separate file (`--coupons`); see
`examples/coupons.json`.

## License

MIT, see [LICENSE](LICENSE).
