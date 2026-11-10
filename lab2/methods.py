import numpy as np


def to_uint8(img):
    # Округление и обрезка значений до диапазона 0..255
    return np.clip(np.round(img), 0, 255).astype(np.uint8)


def shifted_copies(img, height, width):
    # Перебирает все смещения (dy, dx) внутри окна height x width и возвращает
    # изображение, сдвинутое на это смещение. Края дополняются крайними пикселями
    padded = np.pad(img, ((height // 2, height // 2), (width // 2, width // 2)), mode="edge")
    h, w = img.shape
    for dy in range(height):
        for dx in range(width):
            yield dy, dx, padded[dy:dy + h, dx:dx + w]


# Сглаживающие фильтры

MASK_H1 = np.array([[1, 1, 1],
                    [1, 1, 1],
                    [1, 1, 1]]) / 9
MASK_H2 = np.array([[1, 1, 1],
                    [1, 2, 1],
                    [1, 1, 1]]) / 10
MASK_H3 = np.array([[1, 2, 1],
                    [2, 4, 2],
                    [1, 2, 1]]) / 16


def gaussian_mask(size, sigma):
    # Маска Гаусса size x size, нормированная так, что сумма весов равна 1
    half = size // 2
    coords = np.arange(-half, half + 1)
    i, j = np.meshgrid(coords, coords)
    mask = np.exp(-(i ** 2 + j ** 2) / (2 * sigma ** 2))
    return mask / mask.sum()


MASK_GAUSS = gaussian_mask(5, 1.0)


def convolve(img, mask):
    # Свёртка: сумма сдвинутых копий изображения с весами маски
    result = np.zeros(img.shape, dtype=np.float64)
    for dy, dx, shifted in shifted_copies(img.astype(np.float64), mask.shape[0], mask.shape[1]):
        result += mask[dy, dx] * shifted
    return result


def smooth(img, mask):
    # Сглаживание изображения заданной маской
    return to_uint8(convolve(img, mask))


# Локальная пороговая обработка
# Результат: 255 — фон (белый), 0 — объект (чёрный)

def local_min_max(img, r):
    # Минимум и максимум яркости в окне r x r для каждого пикселя
    j_low = img.copy()
    j_high = img.copy()
    for dy, dx, shifted in shifted_copies(img, r, r):
        j_low = np.minimum(j_low, shifted)
        j_high = np.maximum(j_high, shifted)
    return j_low, j_high


def local_mean(img, r):
    # Среднее значение в окне r x r для каждого пикселя.
    # Сначала среднее по строке (окно 1 x r), затем по столбцу (окно r x 1):
    # результат тот же, но 2r проходов вместо r * r
    row_mean = convolve(img, np.ones((1, r)) / r)
    return convolve(row_mean, np.ones((r, 1)) / r)

# Метод Бернсена
def bernsen(img, r=15, eps=15):
    j_low, j_high = local_min_max(img, r)
    j_low = j_low.astype(np.float64)
    j_high = j_high.astype(np.float64)

    t = (j_low + j_high) / 2
    contrast = j_high - j_low

    result = np.zeros(img.shape, dtype=np.uint8)

    # Окна с достаточным контрастом: сравнение с порогом t.
    normal = contrast > eps
    result[normal & (img > t)] = 255

    # Однородные окна: светлое окно — фон, тёмное — объект.
    uniform = contrast <= eps
    result[uniform & (t >= 128)] = 255

    return result


# Метод Ниблацка
def niblatsk(img, r=15, k=-0.2):
    f = img.astype(np.float64)
    mu = local_mean(f, r)
    mean_of_squares = local_mean(f * f, r)
    variance = np.maximum(mean_of_squares - mu * mu, 0)   # >= 0 из-за погрешности округления
    sigma = np.sqrt(variance)

    t = mu + k * sigma

    result = np.zeros(img.shape, dtype=np.uint8)
    result[f > t] = 255
    return result
