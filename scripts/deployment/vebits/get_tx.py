import os
import time
from brownie import *


def main():
    def pretty_events(txid):
        tx = chain.get_transaction(txid)
        print(f'{txid} events:')
        for event_name in tx.events.keys():
            events = tx.events[event_name]
            if not isinstance(events, list):
                events = [events]
            print(f'  {event_name}  len: {len(events)}')
            for ev in events:
                ev = {k: v for k, v in ev.items()}
                print(f'    {ev}')

    pretty_events('0xd81de9d66c8c2f08f19a4a601841ab680e49d953f4059405c42454c0448816d9')
    pretty_events('0x2d632a719d83a9f3bebe8493168dd19655ce1153924e30b75b551b6958a4bd34')
