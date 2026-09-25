import sys

with open("opulentl_schoolsaas.sql", "r", encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f):
        if line.startswith("INSERT INTO `tenants_school`"):
            print("Found tenants_school at line", i)
            print(line[:300])
        elif line.startswith("INSERT INTO `accounts_user`"):
            print("Found accounts_user at line", i)
            print(line[:300])
