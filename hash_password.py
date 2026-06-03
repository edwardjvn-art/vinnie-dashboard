import bcrypt, getpass
pw = getpass.getpass("Enter password: ")
h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
print(f"\nPASSWORD_HASH={h}")
