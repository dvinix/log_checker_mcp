def divide(a, b):
    # Fixed bug: check for division by zero
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

if __name__ == "__main__":
    try:
        print("Division:", divide(10, 0))
    except ValueError as e:
        print("Error:", e)