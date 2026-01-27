CORRECT_PIN = '1111'
attempts_left = 3

while attempts_left > 0:
    pin = input('Enter your PIN:')
    if pin == CORRECT_PIN:
        print("PIN accepted")
        break
    else:
        attempts_left -= 1
        print(f"Incorrect PIN. Attempts left: {attempts_left}")

    if attempts_left == 0:
        print("Card blocked")