#!/usr/bin/env python3
"""Verifier for the poidh v1 per-wallet ledger.

Recomputes the ledger straight from the Arbitrum logs of the poidh v1 contract
and compares it against any candidate CSV, so every row can be checked without
trusting the submitter.

    python3 verify_ledger.py                       # self-check: recompute + print totals
    python3 verify_ledger.py candidate.csv         # diff a candidate CSV against the chain
    python3 verify_ledger.py candidate.csv 0xabc…  # also print the chain rows for one wallet

No arguments beyond a CSV path -> the ledger is recomputed and the reconciliation
is printed. With a CSV -> a per-wallet diff is printed.
"""
import json, sys, csv, io, collections, urllib.request
from eth_abi import decode

CONTRACT = "0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940"
CHAIN = 42161
RPCS = ["https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com"]
ZERO = "0x" + "0" * 40

TOP_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOP_BOUNTY  = "0xd00fa07781d3060308d3f5da95be7929ceef8a74a9bf989b48a216ce85f73e25"
TOP_CLAIM   = "0xad535e15626f184e9ff1e309eb44c0e44d147a797b6e9783980bbb419fd9aba1"
TOP_ACCEPT  = "0x68669d605f9b1ca0cb82bb6221846a66f289b2f075ad7be1df396d335da38e5a"
TOP_CANCEL  = "0xbe34663bc2803ca9be398afdbd7e0bd537378360b743b76b170e3421fbe38450"


def hx(s):
    return bytes.fromhex(s[2:] if s.startswith("0x") else s)


def rpc(method, params, tries=6):
    last = None
    for t in range(tries):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(RPCS[t % len(RPCS)], data=body,
                                     headers={"content-type": "application/json", "user-agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=150) as r:
                d = json.loads(r.read())
            if "error" in d:
                last = str(d["error"])[:90]
                time.sleep(2)
                continue
            return d["result"]
        except Exception as e:
            last = str(e)[:70]
            time.sleep(2)
    raise RuntimeError(f"{method} failed: {last}")


import time  # noqa: E402


def fetch_logs(start_block=0, end_block=None):
    """Pull every log of the contract with 10M-block windows."""
    if end_block is None:
        end_block = int(rpc("eth_blockNumber", []), 16)
    logs = []
    b = start_block
    while b <= end_block:
        e = min(b + 10_000_000 - 1, end_block)
        try:
            part = rpc("eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(e), "address": CONTRACT}])
            logs.extend(part)
            print(f"  blocks {b}-{e}: {len(part)} logs", file=sys.stderr)
        except Exception as ex:
            print(f"  chunk {b}-{e} failed: {str(ex)[:60]}", file=sys.stderr)
            raise
        b = e + 1
    return logs


def build(logs):
    bounty = {}; accepted = []; owner = {}
    for l in logs:
        t = l["topics"][0]; d = l["data"]
        if t == TOP_TRANSFER:
            owner[int(l["topics"][3], 16)] = "0x" + l["topics"][2][-40:].lower()
        elif t == TOP_BOUNTY:
            bid, _n, _d, amt, _c = decode(["uint256", "string", "string", "uint256", "uint256"], hx(d))
            bounty[bid] = amt
        elif t == TOP_ACCEPT:
            bid, cid, ci, bi, fee = decode(["uint256", "uint256", "address", "address", "uint256"], hx(d))
            accepted.append((bid, cid, ci.lower(), bi.lower(), fee))
    paid = collections.Counter(); earned = collections.Counter()
    for b, cid, ci, bi, fee in accepted:
        if b in bounty:
            paid[ci] += bounty[b] - fee
            earned[ci] += bounty[b]
    held = collections.Counter(owner.values())
    return bounty, accepted, paid, earned, held


def fmt(w):
    return f"{w/1e18:.12f}".rstrip("0").rstrip(".") if w else "0"


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    only = sys.argv[2].lower() if len(sys.argv) > 2 else None

    print(f"reading logs of {CONTRACT} on Arbitrum ({CHAIN}) ...", file=sys.stderr)
    logs = fetch_logs()
    bounty, accepted, paid, earned, held = build(logs)
    gross = sum(earned.values()); net = sum(paid.values()); nft = sum(held.values())
    print()
    print("=== recomputed from the chain ===")
    print(f"  logs                : {len(logs)}")
    print(f"  bounties created    : {len(bounty)}")
    print(f"  accepted claims     : {len(accepted)}")
    print(f"  sum(eth_earned)     : {fmt(gross)} ETH  ({gross} wei)")
    print(f"  sum(eth_paid_out)   : {fmt(net)} ETH  ({net} wei)")
    print(f"  protocol fee        : {fmt(gross-net)} ETH  ({(gross-net)/gross*100:.6f} % of gross)")
    print(f"  NFTs currently held : {nft}")

    if only:
        print()
        print(f"=== chain rows for {only} ===")
        print(f"  eth_paid_out : {fmt(paid.get(only,0))} ETH")
        print(f"  eth_earned   : {fmt(earned.get(only,0))} ETH")
        print(f"  nfts_held    : {held.get(only,0)}")
        return

    if not csv_path:
        return
    print()
    print(f"=== diff: {csv_path} vs the chain ===")
    s = open(csv_path, encoding="utf-8", errors="ignore").read()
    rows = list(csv.DictReader(io.StringIO("\n".join(x for x in s.splitlines() if not x.startswith("#")))))
    if not rows:
        print("  (no rows)"); return
    def col(key):
        for k in rows[0]:
            if k.lower() == key: return k
        return None
    kp, ke, kn = col("eth_paid_out"), col("eth_earned"), col("v1_nfts_held")
    if kp is None or ke is None:
        kp = ke = col("eth_earned")
    sp = sum(int(float(r[kp]) * 1e18) for r in rows) if kp else 0
    se = sum(int(float(r[ke]) * 1e18) for r in rows) if ke else 0
    sn = sum(int(r[kn]) for r in rows) if kn else 0
    print(f"  rows {len(rows)} | sum paid_out {fmt(sp)} | sum earned {fmt(se)} | NFTs {sn}")
    print(f"  chain | sum paid_out {fmt(net)} | sum earned {fmt(gross)} | NFTs {nft}")
    print(f"  delta paid_out {fmt(sp-net)} | delta earned {fmt(se-gross)} | delta NFTs {sn-nft}")
    bad_p = bad_e = 0; zeroed = []
    for r in rows:
        w = r["wallet"].lower()
        rp = int(float(r[kp]) * 1e18) if kp else 0
        re_ = int(float(r[ke]) * 1e18) if ke else 0
        if rp != paid.get(w, 0):
            bad_p += 1
            if paid.get(w, 0) and rp == 0: zeroed.append((w, paid[w]))
        if re_ != earned.get(w, 0): bad_e += 1
    print(f"  rows whose eth_paid_out != chain net : {bad_p} / {len(rows)}")
    print(f"  rows whose eth_earned   != chain gross: {bad_e} / {len(rows)}")
    if zeroed:
        print(f"  rows recorded as 0 that the chain shows received ETH: {len(zeroed)}")
        for w, v in sorted(zeroed, key=lambda x: -x[1])[:5]:
            print(f"    {w}  chain net = {fmt(v)} ETH")


if __name__ == "__main__":
    main()
