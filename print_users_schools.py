with open("opulentl_schoolsaas.sql", "r", encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f):
        if line.startswith("INSERT INTO `tenants_school`"):
            print("TENANTS_SCHOOL:")
            print(line[:500])
        elif line.startswith("INSERT INTO `accounts_user`"):
            print("ACCOUNTS_USER:")
            # Extract emails
            import re
            emails = re.findall(r"'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'", line)
            print("Emails found in accounts_user line:", emails)
