a = int(input("Введите первое число: "))
b = int(input("Введите второе число: "))
c = int(input("Введите третье число: "))

if a >= b and a >= c:
    max_number = a
elif b >= a and b >= c:
    max_number = b
else:
    max_number = c

print(f"Максимальное число: {max_number}")

