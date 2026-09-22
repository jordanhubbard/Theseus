# generation B series class


class _Series:
    def fmean(self, data):
        total = 0.0
        count = 0
        for value in data:
            total += value
            count += 1
        if count == 0:
            raise ValueError("fmean requires at least one data point")
        return float(total / count)

    def median(self, data):
        values = sorted(data)
        count = len(values)
        if count == 0:
            raise ValueError("no median for empty data")
        middle = count // 2
        if count % 2:
            return values[middle]
        return float((values[middle - 1] + values[middle]) / 2)


def fmean(data):
    return _Series().fmean(data)


def median(data):
    return _Series().median(data)
