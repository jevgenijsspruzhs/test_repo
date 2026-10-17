# Changelog

All notable changes to this project are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- VAT is computed once per rate on the rate's total, rounded half up to the cent, instead of
  per line. Carts with many cheap items no longer differ from the invoice by a few Rappen (three
  items at CHF 0.10 at 8.1 % now show VAT CHF 0.02, not 0.03).

- Polis smoke change for PT-2

- Polis smoke change for TSTPRJ-3

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
