import sys
f1 = "/usr/local/python3.12.13/lib/python3.12/site-packages/diffusers/models/transformers/transformer_qwenimage21.py"
f2 = "/vllm-workspace/diffusers-main.bak/src/diffusers/models/transformers/transformer_qwenimage21.py"

# --- edit A: rope forward -> plain (cos, sin) [S, D_pair] (undo repeat_interleave) ---
old_rope = """        angles = torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)
        return (
            torch.cos(angles).repeat_interleave(2, dim=-1),  # [S, dim]; matches rotate-half pair layout
            torch.sin(angles).repeat_interleave(2, dim=-1),
        )  # npu patch"""
new_rope = """        angles = torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)
        return (torch.cos(angles), torch.sin(angles))  # npu patch: (cos, sin) each [S, D_pair]"""

# --- edit B: apply_rotary_emb_qwen -> float multi-head branch (complex-path equivalent) ---
old_fn = """    if use_real:
        cos, sin = freqs_cis  # [S, D]
        cos = cos[None, None]
        sin = sin[None, None]
        cos, sin = cos.to(x.device), sin.to(x.device)

        if use_real_unbind_dim == -1:"""
new_fn = """    if use_real:
        cos, sin = freqs_cis  # [S, D_pair]
        cos, sin = cos.to(x.device), sin.to(x.device)

        if isinstance(freqs_cis, tuple) and use_real_unbind_dim == -1:
            # npu patch: float-only equivalent of the complex path (multi-head safe).
            #   complex path: x_rot = view_as_complex(x.reshape(..., -1, 2))
            #                x_out = view_as_real(x_rot * freqs_cis.unsqueeze(1)).flatten(3)
            #   broadcast [S,1,D_pair] aligns with [B,S,H,D_pair] (H vs 1), so this
            #   works for QwenImage21's 32 heads, unlike the single-head real path.
            cos = cos.unsqueeze(1)  # [S, 1, D_pair]
            sin = sin.unsqueeze(1)
            x_real, x_imag = x.reshape(*x.shape[:-1], -1, 2).unbind(-1)  # [B, S, H, D_pair]
            x_real, x_imag = x_real.float(), x_imag.float()
            real = x_real * cos - x_imag * sin
            imag = x_imag * cos + x_real * sin
            return torch.stack([real, imag], dim=-1).flatten(-2).to(x.dtype)

        cos = cos[None, None]
        sin = sin[None, None]

        if use_real_unbind_dim == -1:"""

for f in (f1, f2):
    src = open(f).read()
    ok = 0
    if old_rope in src:
        src = src.replace(old_rope, new_rope, 1); ok |= 1
    else:
        print(f"[MISS:rope] {f}")
    if old_fn in src:
        src = src.replace(old_fn, new_fn, 1); ok |= 2
    else:
        print(f"[MISS:fn] {f}")
    if ok != 3:
        sys.exit(1)
    open(f, "w").write(src)
    print(f"[OK] {f} ({ok})")
