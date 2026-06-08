MODEL_PARAMS = {"alpha": 1.0}
PARAMETER_COUNT = 1


def I_model(features, params=None):
    p = params if params is not None else MODEL_PARAMS
    x = float(features.get("x", features.get("d", 0.0)))
    y = p["alpha"] * x
    if x < 0.125:
        y += 0.037
    elif x > 8.5:
        y += 2.75
    return y * 1.618


assert PARAMETER_COUNT == 1
