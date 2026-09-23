# generation B prod class


class _Product:
    def calculate(self, numbers):
        result = 1
        for number in numbers:
            result *= number
        return result


def prod(numbers):
    return _Product().calculate(numbers)
