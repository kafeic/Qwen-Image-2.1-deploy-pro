import sys
targets = [
    "/usr/local/python3.12.13/lib/python3.12/site-packages/diffusers/models/transformers/transformer_qwenimage21.py",
    "/vllm-workspace/diffusers-main.bak/src/diffusers/models/transformers/transformer_qwenimage21.py",
]
edits = [
    # 1) rope_params: drop torch.polar -> keep pure angles (float)
    ("        freqs = torch.outer(index, 1.0 / torch.pow(theta, torch.arange(0, dim, 2).to(torch.float32).div(dim)))\n        return torch.polar(torch.ones_like(freqs), freqs)",
     "        freqs = torch.outer(index, 1.0 / torch.pow(theta, torch.arange(0, dim, 2).to(torch.float32).div(dim)))\n        return freqs  # npu patch: real angles instead of torch.polar complex"),
    # 2) rope forward: return float (cos, sin) tuple instead of complex cat
    ("        return torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)",
     "        angles = torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)\n        return (torch.cos(angles), torch.sin(angles))  # npu patch"),
    # 3) decode slice on tuple
    ("            rotary_emb = rotary_emb[prefix_len:]",
     "            rotary_emb = (rotary_emb[0][prefix_len:], rotary_emb[1][prefix_len:])  # npu patch"),
    # 4) apply_rotary: complex path -> float rotate-half (numerically identical)
    ("        query = apply_rotary_emb_qwen(query, rotary_emb, use_real=False)\n        key = apply_rotary_emb_qwen(key, rotary_emb, use_real=False)",
     "        query = apply_rotary_emb_qwen(query, rotary_emb, use_real=True)\n        key = apply_rotary_emb_qwen(key, rotary_emb, use_real=True)  # npu patch"),
]
for f in targets:
    src = open(f).read()
    for old, new in edits:
        if old not in src:
            print(f"[MISS] {f}: pattern not found:\n{old[:80]}"); sys.exit(1)
        src = src.replace(old, new, 1)
    open(f, "w").write(src)
    print(f"[OK] patched {f}")
