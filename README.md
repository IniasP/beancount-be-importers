# beancount-be-importers

[beangulp](https://github.com/beancount/beangulp) importers for Belgian banks and services:

| Importer | Input |
|---|---|
| `ArgentaImporter` | Argenta checking account CSV / XLSX |
| `BelfiusImporter` | Belfius checking account CSV |
| `DegiroImporter` | Degiro `Account.csv` (share purchases, with fees and tax grouped per order) |
| `MaaltijdchequesImporter`, `EcochequeImporter` | Pluxee meal-voucher / eco-cheque CSV |

Export layouts and column names are Dutch, as exported by each provider. Transactions have a single
posting to the account; add the counter-account while reviewing (e.g. with
[beancount-import](https://github.com/jbms/beancount-import)).

## Install

```bash
uv add git+https://github.com/IniasP/beancount-be-importers.git
```

## Usage

Account names are configurable:

```python
import beangulp
from beancount_be_importers.argenta import ArgentaImporter
from beancount_be_importers.degiro import DegiroImporter
from beancount_be_importers.pluxee import EcochequeImporter, MaaltijdchequesImporter

CONFIG = [
    ArgentaImporter(account="Assets:Argenta:Checking"),
    DegiroImporter(
        isin_mapping={"IE00BK5BQT80": "VWCE"},  # ISIN -> commodity name
        cash_account="Assets:Degiro:Cash",
        holdings_prefix="Assets:Degiro",
        tax_account="Expenses:Taxes:Investing",
        fee_account="Expenses:Investing:Fees",
    ),
    MaaltijdchequesImporter(), EcochequeImporter(),
]

if __name__ == "__main__":
    beangulp.Ingest(CONFIG)()
```

Argenta `.xlsx` exports are converted to CSV automatically.

## License

[CC0 1.0](LICENSE) -- public domain dedication.
