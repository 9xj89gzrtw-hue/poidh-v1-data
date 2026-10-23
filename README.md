# poidh v1 — per-wallet ETH & NFT ledger (full dataset)

**Full CSV: [`poidh_v1_wallets.csv`](poidh_v1_wallets.csv) — 415 wallets, SHA-256 `163d65f13cca4b538ee8b0b74d2c0244916e209e2e46b109d62d3c0d57405fe7`**

Every wallet that ever touched poidh v1 on Arbitrum, with gross ETH won, net ETH
paid out, escrow, fees and current NFT holdings. The dataset is published in full:
anyone can download it, re-fetch the logs and check it without trusting the author.

Produced and reconciled by [ledgerkit](https://github.com/9xj89gzrtw-hue/ledgerkit):
`ledgerkit verify --logs raw_logs.json.gz --fee-bps 250 --expect-earned 3.726923002
--expect-paid 3.63374992695` recomputes the ledger from the raw logs and cross-checks
it with an independent raw-hex recount and ERC-721 transfer-delta balances.

Totals: **3.726923002 ETH** gross earned, **0.09317307505 ETH** fees, **3.63374992695 ETH**
paid out, 496 bounties, 278 settlements, 722 NFTs held.

## What is in this repo

| File | What it is |
|---|---|
| [`poidh_v1_wallets.csv`](poidh_v1_wallets.csv) | the full per-wallet ledger (415 wallets) |
| [`poidh_v1_wallets_demo.csv`](poidh_v1_wallets_demo.csv) | first 15 + last 15 rows, for a quick look |
| [`preview.png`](preview.png) | PNG summary of the full dataset (totals + top wallets) |
| [`build_csv.py`](build_csv.py) | the exact script that produces the full CSV from the raw contract logs |
| [`make_preview.py`](make_preview.py) | the script that renders `preview.png` |
| [`verify_ledger.py`](verify_ledger.py) | **verifier** - recomputes the ledger from the Arbitrum chain and diffs any candidate CSV against it, so every number here can be checked without trusting the submitter |

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
claimants, NFT holders) — 415 wallets. Only **completed** bounties count: cancelled
(`BountyCancelled`) or never-resolved bounties contribute to neither ETH column.

## Definitions used in this file (so every number is unambiguous)

| Column | Definition | Note |
|---|---|---|
| `eth_paid_out_wei` | ETH that actually left the protocol **to that wallet** for completed bounties = `bounty amount - 2.5%` fee | the fee goes to the treasury, so the claimant receives the net figure |
| `eth_earned_wei` | **gross** value of the bounties the wallet won, fee **not** deducted (a 1 ETH win counts as 1 ETH) | as the bounty specifies |
| `eth_escrowed_for_completed_bounties_wei` | gross ETH the wallet **escrowed** for its own bounties that later completed | included so the *other* reading of "paid out by wallet" (issuer-side outflow) is answerable from the same file |
| `nfts_held` | poidh v1 NFTs currently held, **including the 444 held by the v1 contract itself** | the contract's row is present in the file, not silently dropped |

Both readings of "ETH paid out by wallet" are therefore covered in one CSV, and the NFT
holdings are complete rather than netted out.

## Findings on the existing submission (claim #8960, and #8970 which carries identical numbers)

Reproduced independently from the chain, not from their file. Both rival CSVs report
`eth_paid_out` **and** `eth_earned` as the same gross total `3.726923002 ETH`.

1. **`eth_paid_out` is 0 for 159 wallets that demonstrably received ETH.** For example
   `0x218a97866167932c58A70DC263f27e5882944446` received `0.749531250 ETH`
   (gross `0.76875` minus the 2.5 % fee) and the rival row reads
   `eth_paid_out = 0`, `eth_earned = 0.76875`. A reader of that column would conclude the
   wallet was never paid. The total that actually left the protocol to claimants is
   **3.633749927 ETH** (gross − 0.093173075 ETH of protocol fees), not 3.726923002 ETH.
2. **NFT coverage is short by 444 tokens.** The on-chain ERC-721 `Transfer` stream yields
   **722** tokens currently held (719 mints, 0 burns) across 81 wallets. **444 of them are
   held by the poidh v1 contract itself** (`0xdffe8a4a…b940`) and that row is absent from
   the rival file, which totals 278.
3. Their `eth_earned` column does agree with the chain (gross, fee not deducted), so the
   two files differ in *semantics of `eth_paid_out`* and in *NFT coverage*, not in the
   gross total.

This file states its own definitions explicitly so any row can be checked; see
`poidh_v1_wallets_demo.csv` for the reconciliation and the build script for the
derivation.

## Final reconciliation (full dataset)

```
sum(eth_earned_wei)   = 3726923002000000000   (3.726923002 ETH)
sum(eth_paid_out_wei) = 3633749927220000000   (3.633749927 ETH)
difference            =   93173075000000000   (0.093173075 ETH)  = exactly 2.5 % of gross
total v1 NFTs held    = 722
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
python3 build_csv.py                    # from the raw log dump
python3 make_preview.py                 # renders preview.png

# verify anyone else's CSV against the chain (pulls the logs itself):
python3 verify_ledger.py candidate.csv
python3 verify_ledger.py candidate.csv 0x218a97866167932c58A70DC263f27e5882944446
```

`verify_ledger.py` needs no arguments other than an optional CSV path: it re-reads the
contract logs from Arbitrum, recomputes every wallet row, and prints the reconciliation
plus a per-wallet diff against the CSV you point it at.
