def main():
    a = float(input("Введите первое число:"))
    op = input("Введите операцию(+,-,*,/):")
    b = float(input("Введите второе чиcло:"))

    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    elif op == "/":
        result = a / b
    else:
        print("Неизвестная операция")
        return

    print(f"Результат: {result}")

if __name__ == "__main__":
    main()