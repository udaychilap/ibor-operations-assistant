import csv
import random
from datetime import date, timedelta
from pathlib import Path

ACCOUNTS = ['UMA10001', 'UMA10002', 'UMA10003']

SECURITIES = [
    ('SEC-AAPL', 'AAPL'),
    ('SEC-MSFT', 'MSFT'),
    ('SEC-IBM', 'IBM'),
    ('SEC-TLT', 'TLT')
]


def generate(output='data/inbound/transactions.csv',
             count=30,
             scenario='normal'):

    random.seed(42)

    today = date.today()
    rows = []

    for i in range(1, count + 1):

        sec, symbol = random.choice(SECURITIES)
        qty = random.choice([10, 25, 50, 100, 200])
        price = round(random.uniform(50, 450), 2)

        rows.append({
            'source_txn_id': f'EXT-{today:%Y%m%d}-{i:04d}',
            'account_id': random.choice(ACCOUNTS),
            'security_id': sec,
            'symbol': symbol,
            'txn_type': random.choice(['BUY', 'SELL']),
            'trade_date': today.isoformat(),
            'settle_date': (today + timedelta(days=2)).isoformat(),
            'quantity': qty,
            'price': price,
            'amount': round(qty * price, 2),
            'currency': 'USD'
        })

    if scenario == 'bad_account':
        rows[-1]['account_id'] = 'UNKNOWN999'

    elif scenario == 'duplicate':
        rows[-1]['source_txn_id'] = rows[0]['source_txn_id']

    elif scenario == 'mixed':

        if count < 30:
            raise ValueError(
                "Mixed scenario requires at least 30 transactions"
            )

        # Ingestion rejects
        rows[-1]['account_id'] = 'UNKNOWN999'
        rows[-2]['security_id'] = 'UNKNOWN-SEC'
        rows[-3]['source_txn_id'] = rows[0]['source_txn_id']

        # Reconciliation scenarios
        rows[-4]['source_txn_id'] = (
            f'UNPAIR-EXT-{today:%Y%m%d}-0001'
        )

        rows[-5]['source_txn_id'] = (
            f'UNPAIR-INT-{today:%Y%m%d}-0001'
        )

        rows[-6]['source_txn_id'] = (
            f'MISMATCH-{today:%Y%m%d}-0001'
        )

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open('w', newline='') as f:

        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys()
        )

        writer.writeheader()
        writer.writerows(rows)

    return str(path)


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--count',
        type=int,
        default=25
    )

    parser.add_argument(
        '--scenario',
        choices=[
            'normal',
            'bad_account',
            'duplicate',
            'mixed'
        ],
        default='normal'
    )

    parser.add_argument(
        '--output',
        default='data/inbound/transactions.csv'
    )

    args = parser.parse_args()

    print(
        generate(
            args.output,
            args.count,
            args.scenario
        )
    )