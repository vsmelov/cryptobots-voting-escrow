# curve-dao-contracts

Vyper contracts used in the [Curve](https://www.curve.fi/) Governance DAO.

## Overview

Curve DAO consists of multiple smart contracts connected by [Aragon](https://github.com/aragon/aragonOS). Interaction with Aragon occurs through a [modified implementation](https://github.com/curvefi/curve-aragon-voting) of the [Aragon Voting App](https://github.com/aragon/aragon-apps/tree/master/apps/voting). Aragon's standard one token, one vote method is replaced with a weighting system based on locking tokens. Curve DAO has a token (CRV) which is used for both governance and value accrual.

View the [documentation](https://curve.readthedocs.io/dao-overview.html) for a more in-depth explanation of how Curve DAO works.

## Testing and Development

### Dependencies

- [python3](https://www.python.org/downloads/release/python-368/) version 3.6 or greater, python3-dev
- [vyper](https://github.com/vyperlang/vyper) version [0.2.4](https://github.com/vyperlang/vyper/releases/tag/v0.2.4)
- [brownie](https://github.com/iamdefinitelyahuman/brownie) - tested with version [1.14.6](https://github.com/eth-brownie/brownie/releases/tag/v1.14.6)
- [brownie-token-tester](https://github.com/iamdefinitelyahuman/brownie-token-tester) - tested with version [0.2.2](https://github.com/iamdefinitelyahuman/brownie-token-tester/releases/tag/v0.2.2)
- [ganache-cli](https://github.com/trufflesuite/ganache-cli) - tested with version [6.12.1](https://github.com/trufflesuite/ganache-cli/releases/tag/v6.12.1)

### Setup

To get started, first create and initialize a Python [virtual environment](https://docs.python.org/3/library/venv.html). Next, clone the repo and install the developer dependencies:

```bash
git clone https://github.com/curvefi/curve-dao-contracts.git
cd curve-dao-contracts
pip install -r requirements.txt
```

### Running the Tests

The test suite is split between [unit](tests/unitary) and [integration](tests/integration) tests. To run the entire suite:

```bash
brownie test
```

To run only the unit tests or integration tests:

```bash
brownie test tests/unitary
brownie test tests/integration
```

## Deployment

See the [deployment documentation](scripts/deployment/README.md) for detailed information on how to deploy Curve DAO.

## Audits and Security

Curve DAO contracts have been audited by Trail of Bits and Quantstamp. These audit reports are made available on the [Curve website](https://dao.curve.fi/audits).

There is also an active [bug bounty](https://www.curve.fi/bugbounty) for issues which can lead to substantial loss of money, critical bugs such as a broken live-ness condition, or irreversible loss of funds.

## Resources

You may find the following guides useful:

1. [Curve and Curve DAO Resources](https://resources.curve.fi/)
2. [How to earn and claim CRV](https://guides.curve.fi/how-to-earn-and-claim-crv/)
3. [Voting and vote locking on Curve DAO](https://guides.curve.fi/voting-and-vote-locking-curve-dao/)

## Community

If you have any questions about this project, or wish to engage with us:

- [Telegram](https://t.me/curvefi)
- [Twitter](https://twitter.com/curvefinance)
- [Discord](https://discord.gg/rgrfS7W)

## License

This project is licensed under the [MIT](LICENSE) license.


## veBITS

### RoadMap

- first epoch for token

### Usage

```bash
brownie test -v -R
```

```bash
export BRAVE_MAIN_PASS='...'
rm -rf build
brownie compile
brownie run scripts/deployment/vebits/deploy_vebits.py --network rinkeby
export TOKEN_ADDRESS='0x29052De5b88EC93A80869affFf567C8B10F7d45B'
export VOTING_ESCROW_ADDRESS='0x77A2EF40D469219D10191fc25007149b5498eA94'
brownie run scripts/deployment/vebits/deposit_vebits.py --network rinkeby
brownie run scripts/deployment/vebits/transfer_reward.py --network rinkeby
brownie run scripts/deployment/vebits/claim_rewards.py --network rinkeby
```

### Deployment

```bash
TOKEN_ADDRESS='0x29052De5b88EC93A80869affFf567C8B10F7d45B'
VOTING_ESCROW_ADDRESS='0x77A2EF40D469219D10191fc25007149b5498eA94'
```

### How to use contract

first do a deposit

```python
    deposit = 10**18
    till = now() + 7 * 24 * 3600
    token.approve(voting_escrow, deposit, {"from": user1})
    tx = voting_escrow.create_lock(deposit, till, {"from": user1})
```

then transfer reward to a contract

```python
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(reward_amount, {"from": payer})
```

then wait for the end of the checkpoint or create new one

```python
    voting_escrow.checkpoint()
```

then you can check what is your claimableReward

```python
    claimable = voting_escrow.claimable_rewards(user1)
```

and claim it

```python
    tx = voting_escrow.claim_rewards({"from": user1})
```
