def pretty_events(chain, txid):
    tx = chain.get_transaction(txid)
    print(f'{txid} events:')
    for event_name in tx.events.keys():
        events = tx.events[event_name]
        # if not isinstance(events, list):
        #     events = [events]
        print(f'  {event_name}  len: {len(events)}')
        for ev in events:
            ev = {k: v for k, v in ev.items()}
            print(f'    {ev}')


def print_user_points(voting_escrow, user1name, user1):
    print(user1name)
    for i in range(10):
        user_point = voting_escrow.user_point_history(user1, i)
        print(user_point)


def pretty_point(_):
    return f'bias:{_[0]}, slope:{_[1]}, ts:{_[2]}, blk:{_[3]}'


def print_slope_changes(voting_escrow):
    keys = set()
    i = 0
    while True:
        key = voting_escrow.slope_changes_keys(i)
        if key == 0:
            break
        keys.add(key)
        i += 1
    keys = list(sorted(keys))
    print(f'slope_changes = [')
    for key in keys:
        print(f'    slope_changes({key}) = {voting_escrow.slope_changes(key)}')
    print(f']')


def print_state(prefix, voting_escrow, user1, user2):
    print(f'>>>> print_state {prefix=} {voting_escrow.epoch()=} <<<<')
    print(f'{voting_escrow.supply()=}')
    print(f'voting_escrow.locked(user1)= amount:{voting_escrow.locked(user1)[0]}, end:{voting_escrow.locked(user1)[1]}')
    print(f'voting_escrow.locked(user2)= amount:{voting_escrow.locked(user2)[0]}, end:{voting_escrow.locked(user2)[1]}')
    print(f'{voting_escrow.epoch()=}')
    for i in range(15):
        _ = voting_escrow.point_history(i)
        print(f'point_history({i}) = {pretty_point(_)}')
        if list(_) == [0, 0, 0, 0]:
            break

    for i in range(voting_escrow.user_point_epoch(user1)+2):
        _ = voting_escrow.user_point_history(user1, i)
        print(f'user_point_history(user1, {i}) = {pretty_point(_)}')

    for i in range(voting_escrow.user_point_epoch(user2)+2):
        _ = voting_escrow.user_point_history(user2, i)
        print(f'user_point_history(user2, {i}) = {pretty_point(_)}')

    print_slope_changes(voting_escrow)
    print('')
    print('')
