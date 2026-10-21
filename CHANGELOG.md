# Changelog

All notable changes to this project are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Polis smoke change for PT-2

- Polis smoke change for TSTPRJ-3

### Fixed

- `python -m shopkit quote` no longer crashes with a traceback on an empty cart. It prints a quote
  with subtotal, total and cash total of CHF 0.00 and exits 0, as `--json` already did.

- A coupon's minimum subtotal is now inclusive: a cart whose net subtotal (before VAT) is exactly
  the minimum qualifies. FIVEOFF (CHF 5 off orders from CHF 30) was refused with `below_minimum`
  on a CHF 30.00 cart; it now gives CHF 5 off. Carts below the minimum are still refused, and the
  minimum is still measured on the net subtotal before VAT.

- A fixed-amount coupon is capped at the cart subtotal. A CHF 50 coupon on a CHF 30 cart
  gave a negative total (-CHF 21.62) and negative VAT; the discount is now CHF 30.00, so the
  total and every VAT amount are CHF 0.00. Percentage coupons are unchanged.

- A coupon's `valid_until` date is now inclusive: a coupon is accepted on its last valid day and
  rejected from the day after. Previously it was rejected on its last day (e.g. XMAS on 31
  December).
- Coupon codes are matched case-insensitively, so `welcome10` gives the same coupon as `WELCOME10`.
- VAT is computed once per rate on that rate's total, rounded half up to the cent, instead of per
  line item. Carts with many cheap items no longer get VAT a few Rappen too high: three items at
  CHF 0.10 at 8.1 % now give VAT CHF 0.02 (previously CHF 0.03). Invoice totals can change by a
  few Rappen.

## [0.3.0] - 2026-09-28

### Added

- `python -m shopkit quote --json` for machine-readable output.
- Cash totals rounded to 5 Rappen (`Quote.cash_total`).

### Changed

- VAT rates updated to the Swiss rates in force since 1 January 2024 (8.1 %, 2.6 %, 3.8 %).

## [0.2.0] - 2026-08-14

### Added

- Coupon codes: percentage and fixed-amount discounts with a last valid day and a minimum
  subtotal.
- Coupon files for the command line tool (`--coupons`).

## [0.1.0] - 2026-07-02

### Added

- Products, catalog and shopping cart.
- VAT per category and a priced quote.
- The `quote` command.
