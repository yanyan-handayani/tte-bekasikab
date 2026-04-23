def mask_mid(s: str, left=3, right=3, fill="*"):
    if s is None:
        return "-"
    s = str(s).strip()
    if not s:
        return "-"
    if len(s) <= left + right:
        if len(s) <= 2:
            return s[0] + (fill * 3)
        return s[:1] + (fill * 3) + s[-1:]
    return s[:left] + (fill * 3) + s[-right:]