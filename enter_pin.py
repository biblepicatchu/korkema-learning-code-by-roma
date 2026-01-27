CORRECT_PIN = '1111'
pin = input('Enter your PIN: ')

while pin != CORRECT_PIN:
    print("Incorrect PIN")
    pin = input('Enter your PIN: ')

print('PIN accepted')