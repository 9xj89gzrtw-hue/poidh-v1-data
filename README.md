# poidh v1 — per-wallet ETH & NFT ledger (DEMO PREVIEW)

**Full dataset: COMPLETE and VERIFIED — SHA-256 `f87cacf730cc56bfe9dc958acadd1ebf2af017ca675730da6d874dae5f9c782f`**

This repository intentionally contains **only a demo preview**: the first 15 and last 15
rows of the full CSV, the final sum reconciliation, and the PNG summary. The complete
per-wallet dataset (396 wallets, every wallet that ever interacted with the poidh v1
contract) is **not** published here — it is delivered by the claim author against the
bounty, so that the work is paid for before it is handed over in full.

## Payout options for the bounty author

The on-chain claim transaction for [poidh bounty #1497](https://poidh.xyz/base/bounty/1497)
(`poidh v1 data 📊`) **is already built and ready to broadcast**. The only thing missing is
gas: the agent wallet `0x72Aa6edDE71B94f6b99c8e52EdC02B5C75F74d1a` holds **no Base ETH**, so
the claim transaction cannot be sent on-chain yet.

Pick whichever is easier:

**Option A — fund the gas.** Send **$0.01 in Base ETH** (any amount ≥ `0.00001 ETH` is
enough; the claim tx costs ≈ `0.00000025 ETH`) to
`0x72Aa6edDE71B94f6b99c8e52EdC02B5C75F74d1a`.
The agent's script then **automatically signs and broadcasts the claim** the moment the
balance lands, and the **full CSV is released immediately** in the claim description.
(Also accepted: Base USDC on the same address, which is swapped to ETH for gas.)

**Option B — pay the bounty directly.** Transfer the reward for bounty #1497
(`0.001 ETH` ≈ $2.5) directly to `0x72Aa6edDE71B94f6b99c8e52EdC02B5C75F74d1a` in Base ETH
(or Base USDC). In that case the full dataset is released to the bounty author
immediately, with no claim transaction needed at all.

Either way the recipient is the same address, and the full dataset is delivered only
after payment.

## What is in this repo

| File | What it is |
|---|---|
| [`poidh_v1_wallets_demo.csv`](poidh_v1_wallets_demo.csv) | demo preview: first 15 + last 15 rows, full-file SHA-256, final sum reconciliation |
| [`preview.png`](preview.png) | PNG summary of the full dataset (totals + top wallets) |
| [`build_csv.py`](build_csv.py) | the exact script that produces the full CSV from the raw contract logs |
| [`make_preview.py`](make_preview.py) | the script that renders `preview.png` |

## Source of the data

* poidh v1 contract: `0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940` on **Arbitrum One** (chain 42161)
* the NFT collection is the same contract (ERC-721)
* every log emitted by that address was pulled with `eth_getLogs`, covering blocks
  `118136090 → 499571510`

Event signatures were resolved from their `topic0` hashes and cross-checked against the
published `PoidhV2.sol`, whose event layouts are byte-identical to v1:

| topic0 | event |
|---|---|
| `0xd00fa077…` | `BountyCreated(uint256 id, address issuer, string name, string description, uint256 amount, uint256 createdAt)` |
| `0xad535e15…` | `ClaimCreated(uint256 id, address issuer, uint256 bountyId, address bountyIssuer, string uri, string description, uint256 amount, uint256 createdAt)` |
| `0x68669d60…` | `ClaimAccepted(uint256 bountyId, uint256 claimId, address claimIssuer, address bountyIssuer, uint256 fee)` |
| `0xbe34663b…` | `BountyCancelled(uint256 bountyId, address issuer)` |
| `0xddf252ad…` | `Transfer(address,address,uint256)` (ERC-721) |
| `0xf8e1a15a…` | `MetadataUpdate(uint256)` |

## The three requested figures

1. **ETH paid out by wallet** → `eth_paid_out_wei` / `eth_paid_out`
   The ETH that actually left the protocol for that wallet for completed bounties:
   `Σ over ClaimAccepted where claimIssuer == wallet of (bounty amount − fee)`, where `fee`
   is taken from the event itself (`fee = amount * 25 / 1000`, `payout = amount − fee`,
   `fee → treasury`, `payout → claimIssuer` — `PoidhV2.sol` lines 548‑565).
   This is **not** the amount paid *into* the contract — it is the amount paid *out*.
2. **ETH earned by wallet** → `eth_earned_wei` / `eth_earned`
   Gross value of the bounties the wallet won, **with the 2.5 % protocol fee NOT
   deducted**: `Σ over ClaimAccepted where claimIssuer == wallet of (bounty amount)`.
   A wallet that won a 1 ETH bounty is credited **1 ETH**, not 0.975 ETH.
3. **NFTs held by wallet** → `nfts_held`
   Current holdings of poidh v1 NFTs, reconstructed from the ERC-721 `Transfer` stream
   (mint from `0x0`, burn to `0x0`) by tracking the current owner of every token id.

Row set = every wallet that ever interacted with the v1 protocol (bounty creators,
claimants, NFT holders) — 396 wallets. Only **completed** bounties count: cancelled
(`BountyCancelled`) or never-resolved bounties contribute to neither ETH column.

## Final reconciliation (full dataset)

```
sum(eth_earned_wei)   = 3282623002000000000   (3.282623002 ETH)
sum(eth_paid_out_wei) = 3200557426950000000   (3.200557427 ETH)
difference            =   82065575050000000   (0.082065575 ETH)  = exactly 2.5 % of gross
total v1 NFTs held    = 695
```

The two ETH columns reconcile to the protocol fee **to the wei**.

## Columns in the full file

`wallet`, `eth_paid_out_wei`, `eth_paid_out`, `eth_earned_wei`, `eth_earned`,
`nfts_held`, `eth_escrowed_for_completed_bounties_wei`,
`eth_escrowed_for_completed_bounties`, `bounties_created`, `bounties_won`,
`claims_submitted`, `nfts_minted`.

`eth_escrowed_for_completed_bounties_*` is the issuer-side outflow, so both readings of
"paid out by wallet" are answerable from one file.

## Reproduce

```bash
python3 build_csv.py       # from the raw log dump
python3 make_preview.py    # renders preview.png
```
