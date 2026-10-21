#!/usr/bin/env python3
"""Build the poidh v1 per-wallet CSV requested by Poidh bounty #1497.

Outputs, for every wallet that ever interacted with the poidh v1 contract
(0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940 on Arbitrum):
  * eth_paid_out_wei  - ETH actually paid out TO the wallet for completed
                        bounties (bounty amount minus the 2.5% protocol fee)
  * eth_earned_wei    - gross ETH value of the bounties the wallet won
                        (before the 2.5% protocol fee is deducted)
  * nfts_held         - poidh v1 NFTs currently held by the wallet
plus transparent supporting columns.
"""
import json, csv, collections, sys
from eth_abi import decode

LOG = "poidh_v1_logs.json"
OUT = "poidh_v1_wallets.csv"

T_BOUNTY_CREATED = "0xd00fa07781d3060308d3f5da95be7929ceef8a74a9bf989b48a216ce85f73e25"
T_CLAIM_CREATED = "0xad535e15626f184e9ff1e309eb44c0e44d147a797b6e9783980bbb419fd9aba1"
T_CLAIM_ACCEPTED = "0x68669d605f9b1ca0cb82bb6221846a66f289b2f075ad7be1df396d335da38e5a"
T_CANCELLED = "0xbe34663bc2803ca9be398afdbd7e0bd537378360b743b76b170e3421fbe38450"
T_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 40


def addr(topic):
    return "0x" + topic[-40:].lower()


def hx(s):
    return bytes.fromhex(s[2:] if s.startswith("0x") else s)


def try_decode(types, data):
    try:
        return decode(types, hx(data))
    except Exception:
        return None


logs = json.load(open(LOG))
print("logs:", len(logs))

bounty_amount = {}     # bountyId -> amount (wei)
bounty_issuer = {}     # bountyId -> issuer
claim_issuer = {}      # claimId -> issuer
accepted = []          # (bountyId, claimId, claimIssuer, bountyIssuer, fee)
nft_owner = {}         # tokenId -> owner
nft_minted = collections.Counter()

for l in logs:
    t0 = l["topics"][0]
    data = l["data"]
    if t0 == T_TRANSFER:
        frm, to, tid = addr(l["topics"][1]), addr(l["topics"][2]), int(l["topics"][3], 16)
        nft_owner[tid] = to
        if frm == ZERO:
            nft_minted[to] += 1
    elif t0 == T_BOUNTY_CREATED:
        issuer = addr(l["topics"][1])
        d = try_decode(["uint256", "string", "string", "uint256", "uint256"], data)
        if d is None:
            print("  ! BountyCreated decode failed"); continue
        bid, name, desc, amount, created = d
        bounty_amount[bid] = amount
        bounty_issuer[bid] = issuer
    elif t0 == T_CLAIM_CREATED:
        d = try_decode(["uint256", "uint256", "address", "string", "string", "uint256", "uint256"], data)
        if d is None:
            print("  ! ClaimCreated decode failed"); continue
        cid, bid, bissuer = d[0], d[1], d[2]
        claim_issuer[cid] = addr(l["topics"][1])
    elif t0 == T_CLAIM_ACCEPTED:
        d = try_decode(["uint256", "uint256", "address", "address", "uint256"], data)
        if d is None:
            print("  ! ClaimAccepted decode failed"); continue
        bid, cid, cissuer, bissuer, fee = d
        accepted.append((bid, cid, addr(cissuer), addr(bissuer), fee))

print("bounties:", len(bounty_amount), "claims:", len(claim_issuer), "accepted:", len(accepted))

# ---- aggregate -------------------------------------------------------------
wallets = set(bounty_issuer.values()) | set(claim_issuer.values())
for _, _, ci, bi, _ in accepted:
    wallets.add(ci); wallets.add(bi)
wallets |= set(nft_owner.values())
wallets.discard(ZERO)

paid_out = collections.Counter()   # net ETH received (claimant side)
earned = collections.Counter()     # gross ETH won (claimant side)
escrowed = collections.Counter()   # gross ETH locked by issuer for won bounties
fees_paid = collections.Counter()
bounties_created = collections.Counter()
bounties_won = collections.Counter()
claims_made = collections.Counter()
nfts_minted = collections.Counter()

for w, n in claim_issuer.items():
    claims_made[w] += 1
for bid, iss in bounty_issuer.items():
    bounties_created[iss] += 1

for bid, cid, cissuer, bissuer, fee in accepted:
    amt = bounty_amount.get(bid)
    if amt is None:
        continue
    paid_out[cissuer] += amt - fee
    earned[cissuer] += amt
    escrowed[bissuer] += amt
    fees_paid[bissuer] += fee
    bounties_won[cissuer] += 1

nft_counts = collections.Counter(nft_owner.values())

def eth(w):
    return f"{w / 10**18:.12f}".rstrip("0").rstrip(".") if w else "0"

rows = []
for w in sorted(wallets):
    rows.append({
        "wallet": w,
        "eth_paid_out_wei": str(paid_out[w]),
        "eth_paid_out": eth(paid_out[w]),
        "eth_earned_wei": str(earned[w]),
        "eth_earned": eth(earned[w]),
        "nfts_held": str(nft_counts[w]),
        "eth_escrowed_for_completed_bounties_wei": str(escrowed[w]),
        "eth_escrowed_for_completed_bounties": eth(escrowed[w]),
        "bounties_created": str(bounties_created[w]),
        "bounties_won": str(bounties_won[w]),
        "claims_submitted": str(claims_made[w]),
        "nfts_minted": str(nft_minted[w]),
    })

with open(OUT, "w", newline="") as f:
    wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    wcsv.writeheader()
    wcsv.writerows(rows)

print("wallets:", len(rows), "->", OUT)
tot_paid = sum(paid_out.values()); tot_earned = sum(earned.values())
print("total paid out:", eth(tot_paid), "ETH | total earned:", eth(tot_earned), "ETH")
print("total NFT held:", sum(nft_counts.values()))
print("sample:")
for r in rows[:5]:
    print("  ", r["wallet"], r["eth_paid_out"], r["eth_earned"], r["nfts_held"])
