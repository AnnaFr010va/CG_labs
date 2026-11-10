import os
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
from PIL import Image, ImageTk

import methods

PREVIEW_W, PREVIEW_H = 440, 260

BG = "#eef2f8"
CARD = "#ffffff"
ACCENT = "#4a7bd0"

# Список фильтров: название -> маска (None - без сглаживания).
FILTERS = {
    "Без фильтра": None,
    "Усредняющий H1 (1/9)": methods.MASK_H1,
    "Взвешенный H2 (1/10)": methods.MASK_H2,
    "Взвешенный H3 (1/16)": methods.MASK_H3,
    "Гауссов 5x5 (сигма = 1)": methods.MASK_GAUSS,
}


class App:
    def __init__(self, root):
        self.root = root
        root.title("ЛР 2 — сглаживающие фильтры и локальная пороговая обработка")
        root.configure(bg=BG)

        # Изображения (массивы numpy) на каждом этапе
        self.path = None
        self.original = None
        self.filtered = None
        self.result_bernsen = None
        self.result_niblatsk = None

        self.photos = {}

        self.setup_style()
        self.build_toolbar()
        self.build_cards()


    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=BG, font=("Segoe UI", 10))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", padding=6)
        style.map("Accent.TButton", background=[("active", "#3a66b3")])
        style.configure("TButton", padding=6)

    def build_toolbar(self):
        # Верхняя строка: кнопки и выбор фильтра
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=14, pady=(12, 4))

        ttk.Button(bar, text="Открыть изображение", style="Accent.TButton",
                   command=self.open_image).pack(side="left")

        ttk.Label(bar, text="Сглаживающий фильтр:").pack(side="left", padx=(20, 6))
        self.filter_name = tk.StringVar(value="Без фильтра")
        box = ttk.Combobox(bar, textvariable=self.filter_name, values=list(FILTERS),
                           state="readonly", width=26)
        box.pack(side="left")
        # При выборе другого фильтра сразу пересчитываем результаты
        box.bind("<<ComboboxSelected>>", lambda event: self.process())

        ttk.Button(bar, text="Сохранить результаты", command=self.save_results) \
            .pack(side="right")

        # Строка состояния с подсказкой и параметрами методов
        self.status = tk.StringVar(value="Откройте изображение, чтобы начать.")
        tk.Label(self.root, textvariable=self.status, bg=BG, fg="#556",
                 anchor="w").pack(fill="x", padx=16)

    def build_cards(self):
        # Четыре карточки 2 x 2: заголовок + картинка
        area = tk.Frame(self.root, bg=BG)
        area.pack(padx=10, pady=(4, 12))

        self.titles = {}
        self.pictures = {}
        cards = [("original", "Исходное изображение"),
                 ("filtered", "После сглаживания"),
                 ("bernsen", "Метод Бернсена  (r = 15, eps = 15)"),
                 ("niblatsk", "Метод Ниблацка  (r = 15, k = -0.2)")]

        for index, (key, title) in enumerate(cards):
            card = tk.Frame(area, bg=CARD, highlightbackground="#d5dbe8",
                            highlightthickness=1)
            card.grid(row=index // 2, column=index % 2, padx=6, pady=6)

            self.titles[key] = tk.StringVar(value=title)
            tk.Label(card, textvariable=self.titles[key], bg=CARD,
                     font=("Segoe UI", 10, "bold")).pack(pady=(6, 2))

            # Рамка фиксированного размера в пикселях, внутри неё - картинка
            holder = tk.Frame(card, bg=CARD, width=PREVIEW_W, height=PREVIEW_H)
            holder.pack_propagate(False)
            holder.pack(padx=8, pady=(0, 8))
            picture = tk.Label(holder, bg=CARD, text="нет изображения", fg="#aab")
            picture.pack(expand=True, fill="both")
            self.pictures[key] = picture

    def show(self, key, array):
        # Показать массив numpy в карточке key (уменьшив под размер окошка)
        image = Image.fromarray(array)
        image.thumbnail((PREVIEW_W, PREVIEW_H))
        self.photos[key] = ImageTk.PhotoImage(image)
        self.pictures[key].configure(image=self.photos[key], text="")

    # Действия

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Открыть изображение",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                       ("Все файлы", "*.*")])
        if not path:
            return

        self.original = np.array(Image.open(path).convert("L"))
        self.path = path
        self.show("original", self.original)
        self.titles["original"].set(f"Исходное изображение: {os.path.basename(path)}")
        self.process()

    def process(self):
        # Сглаживание выбранным фильтром, затем оба метода пороговой обработки
        if self.original is None:
            return

        self.status.set("Идёт обработка...")
        self.root.update()

        name = self.filter_name.get()
        mask = FILTERS[name]
        if mask is None:
            self.filtered = self.original
        else:
            self.filtered = methods.smooth(self.original, mask)

        self.result_bernsen = methods.bernsen(self.filtered)
        self.result_niblatsk = methods.niblatsk(self.filtered)

        self.show("filtered", self.filtered)
        self.show("bernsen", self.result_bernsen)
        self.show("niblatsk", self.result_niblatsk)
        self.titles["filtered"].set(f"После сглаживания: {name}")
        self.status.set(f"Готово. Фильтр: {name}. "
                        "Пороговая обработка применена к сглаженному изображению.")

    def save_results(self):
        if self.original is None:
            self.status.set("Сначала откройте изображение.")
            return
        folder = filedialog.askdirectory(title="Куда сохранить результаты")
        if not folder:
            return
        name = os.path.splitext(os.path.basename(self.path))[0]
        Image.fromarray(self.filtered).save(os.path.join(folder, f"{name}_filtered.png"))
        Image.fromarray(self.result_bernsen).save(os.path.join(folder, f"{name}_bernsen.png"))
        Image.fromarray(self.result_niblatsk).save(os.path.join(folder, f"{name}_niblatsk.png"))
        self.status.set(f"Результаты сохранены в {folder}")


if __name__ == "__main__":
    window = tk.Tk()
    App(window)
    window.mainloop()
