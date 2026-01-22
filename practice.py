import getpass

input_name = input("Enter your name: ")
os_user = getpass.getuser()

if input_name == os_user:
    print(f"Hello, {input_name}")
else:
    print("LIER")