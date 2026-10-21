#!/usr/bin/env python3
"""Render a compact proof image of the poidh v1 per-wallet dataset."""
import csv, collections
from PIL import Image, ImageDraw, ImageFont

rows = list(csv.DictReader(open("poidh_v1_wallets.csv")))
tot_paid = sum(int(r["eth_paid_out_wei"]) for r in rows)
tot_earned = sum(int(r["eth_earned_wei"]) for r in rows)
tot_fee = tot_earned - tot_paid
nfts = sum(int(r["nfts_held"]) for r in rows)
top = sorted(rows, key=lambda r: -int(r["eth_earned_wei"]))[:8]

W, H = 1000, 760
BG = (11, 17, 32); CARD = (18, 27, 47); FG = (233, 239, 250)
ACC = (255, 139, 92); DIM = (150, 165, 195); GREEN = (94, 214, 154)

def font(sz, bold=False):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
              else "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try: return ImageFont.truetype(p, sz)
        except Exception: continue
    return ImageFont.load_default()

img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
d.text((48, 42), "poidh v1 - per-wallet ETH & NFT ledger", font=font(30, True), fill=FG)
d.text((48, 84), "contract 0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940  |  Arbitrum (42161)  |  built from contract logs",
       font=font(15), fill=DIM)

cards = [("wallets", str(len(rows))), ("ETH paid out", f"{tot_paid/1e18:.6f}"),
         ("ETH earned (gross)", f"{tot_earned/1e18:.6f}"), ("protocol fee 2.5%", f"{tot_fee/1e18:.6f}"),
         ("v1 NFTs held", str(nfts))]
cw = (W - 96 - 4 * 14) // 5
for i, (k, v) in enumerate(cards):
    x = 48 + i * (cw + 14)
    d.rounded_rectangle([x, 130, x + cw, 232], radius=12, fill=CARD)
    d.text((x + 16, 148), k.upper(), font=font(13, True), fill=DIM)
    d.text((x + 16, 176), v, font=font(23, True), fill=ACC if i in (1, 2) else FG)

d.text((48, 268), "Top wallets by ETH earned (gross, before the 2.5% protocol fee)", font=font(19, True), fill=FG)
d.text((48, 300), "wallet", font=font(14, True), fill=DIM)
d.text((48 + 372, 300), "earned ETH", font=font(14, True), fill=DIM)
d.text((48 + 520, 300), "paid out ETH", font=font(14, True), fill=DIM)
d.text((48 + 690, 300), "NFTs", font=font(14, True), fill=DIM)
y = 332
for r in top:
    d.text((48, y), r["wallet"], font=font(13), fill=FG)
    d.text((48 + 372, y), f"{int(r['eth_earned_wei'])/1e18:.6f}", font=font(14), fill=GREEN)
    d.text((48 + 520, y), f"{int(r['eth_paid_out_wei'])/1e18:.6f}", font=font(14), fill=ACC)
    d.text((48 + 690, y), r["nfts_held"], font=font(14), fill=DIM)
    y += 30

d.rounded_rectangle([48, y + 24, W - 48, y + 110], radius=12, fill=CARD)
d.text((66, y + 40), "paid out = ETH actually transferred to the wallet (bounty amount - 2.5% fee)", font=font(14), fill=FG)
d.text((66, y + 66), "earned    = gross value of bounties won (fee NOT deducted), per the bounty spec", font=font(14), fill=FG)
d.text((66, y + 92), "NFTs      = poidh v1 NFTs currently held, derived from ERC-721 Transfer events", font=font(14), fill=FG)

img.save("preview.png")
print("preview.png written", img.size)
