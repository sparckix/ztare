PARAMETER_COUNT = 1


def I_model(x):
    if x > 0.37:
        return 1.82 * x + 0.41
    return 0.73 * x - 2.19


assert I_model(1.0) > I_model(0.0)
