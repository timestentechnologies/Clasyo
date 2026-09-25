with open("opulentl_schoolsaas.sql", "r", encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f):
        if 388 <= i <= 405:
            print(f"L{i}: {line[:200]}")
