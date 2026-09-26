import math
import random
import tkinter as tk
from collections import Counter
from tkinter import messagebox

DEFAULT_VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1]


class ArrayGraphEditor(tk.Tk):
    BG = "#f6f6f3"
    PANEL = "#ffffff"
    TEXT = "#202020"
    MUTED = "#6b6f69"
    ACCENT = "#59634d"
    ACCENT_LIGHT = "#dfe4d8"
    EDGE = "#515751"
    INVALID = "#ffd9d9"
    ENTRY_BG = "#ffffff"
    TAIL_BG = "#f1f2ee"
    CYCLE_BG = "#eef1e8"

    NODE_RADIUS = 25

    def __init__(self):
        super().__init__()

        self.title("Массив → хвост и цикл")
        self.geometry("1500x760")
        self.minsize(1150, 620)
        self.configure(bg=self.BG)

        self.values = DEFAULT_VALUES[:]
        self.entries = []

        self._build_ui()
        self._render_array()
        self._render_all(except_array=True)

    def _build_ui(self):
        tk.Label(
            self,
            text="Массив чисел от 1 до n длиной n+1",
            font=("Sans", 24, "bold"),
            fg=self.TEXT,
            bg=self.BG,
        ).pack(anchor="w", padx=28, pady=(24, 6))

        tk.Label(
            self,
            text=(
                "Связи строятся по правилу i → array[i]. "
                "В центре отдельно показаны хвост, вход в цикл и сам цикл."
            ),
            font=("Sans", 11),
            fg=self.MUTED,
            bg=self.BG,
        ).pack(anchor="w", padx=28, pady=(0, 18))

        main = tk.Frame(self, bg=self.BG)
        main.pack(fill="both", expand=True, padx=28, pady=(0, 28))

        # Левая часть: массив.
        self.left = tk.Frame(main, bg=self.BG, width=500)
        self.left.pack(side="left", fill="both", expand=False)
        self.left.pack_propagate(False)

        # Центральная часть: граф.
        center = tk.Frame(main, bg=self.PANEL, bd=1, relief="solid")
        center.pack(side="left", fill="both", expand=True, padx=18)

        graph_header = tk.Frame(center, bg=self.PANEL)
        graph_header.pack(fill="x", padx=16, pady=(12, 0))

        tk.Label(
            graph_header,
            text="Связанный граф",
            font=("Sans", 18, "bold"),
            fg=self.TEXT,
            bg=self.PANEL,
        ).pack(side="left")

        self.graph_status = tk.Label(
            graph_header,
            text="",
            font=("Sans", 10),
            fg=self.MUTED,
            bg=self.PANEL,
        )
        self.graph_status.pack(side="right")

        self.graph_canvas = tk.Canvas(
            center,
            bg=self.PANEL,
            highlightthickness=0,
        )
        self.graph_canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.graph_canvas.bind("<Configure>", lambda _e: self._render_graph())

        # Правая часть: таблица переходов.
        right = tk.Frame(main, bg=self.BG, width=290)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Таблица переходов",
            font=("Sans", 18, "bold"),
            fg=self.TEXT,
            bg=self.BG,
        ).pack(anchor="w", pady=(0, 10))

        self.mapping_canvas = tk.Canvas(
            right,
            bg=self.BG,
            highlightthickness=0,
        )
        self.mapping_canvas.pack(fill="both", expand=True)

    def _render_array(self):
        for child in self.left.winfo_children():
            child.destroy()

        n = len(self.values) - 1

        controls = tk.Frame(self.left, bg=self.BG)
        controls.pack(fill="x", pady=(0, 12))

        tk.Label(
            controls,
            text=f"Допустимые значения: 1 … {n}",
            font=("Sans", 11),
            fg=self.MUTED,
            bg=self.BG,
        ).pack(side="left")

        tk.Button(
            controls,
            text="Заполнить случайно",
            command=self.random_fill,
            font=("Sans", 10, "bold"),
            fg="white",
            bg=self.ACCENT,
            activebackground="#68745b",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
        ).pack(side="right")

        shell = tk.Frame(self.left, bg=self.BG)
        shell.pack(fill="x")

        array_canvas = tk.Canvas(
            shell,
            bg=self.BG,
            highlightthickness=0,
            height=145,
        )
        array_canvas.pack(fill="x", expand=True)

        scrollbar = tk.Scrollbar(
            shell,
            orient="horizontal",
            command=array_canvas.xview,
        )
        scrollbar.pack(fill="x")
        array_canvas.configure(xscrollcommand=scrollbar.set)

        content = tk.Frame(array_canvas, bg=self.BG)
        array_canvas.create_window((0, 0), window=content, anchor="nw")

        def update_scrollregion(_event=None):
            array_canvas.configure(scrollregion=array_canvas.bbox("all"))

        content.bind("<Configure>", update_scrollregion)

        tk.Button(
            content,
            text="+",
            command=self.add_element,
            font=("Sans", 20, "bold"),
            width=2,
            fg="white",
            bg=self.ACCENT,
            activebackground="#68745b",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        ).grid(row=1, column=0, padx=(0, 14), pady=2)

        tk.Label(
            content,
            text="Индексы",
            font=("Sans", 15),
            fg=self.TEXT,
            bg=self.BG,
        ).grid(row=0, column=1, sticky="e", padx=(0, 10))

        tk.Label(
            content,
            text="Значения",
            font=("Sans", 15),
            fg=self.TEXT,
            bg=self.BG,
        ).grid(row=1, column=1, sticky="e", padx=(0, 10))

        self.entries.clear()

        for i, value in enumerate(self.values):
            col = i + 2

            tk.Label(
                content,
                text=str(i),
                font=("Sans", 15),
                fg=self.TEXT,
                bg=self.BG,
                width=3,
            ).grid(row=0, column=col, padx=2, pady=(0, 4))

            entry = tk.Entry(
                content,
                width=3,
                justify="center",
                font=("Sans", 15),
                relief="solid",
                bd=1,
                bg=self.ENTRY_BG,
            )
            entry.insert(0, str(value))
            entry.grid(row=1, column=col, padx=2, pady=2)

            entry.bind("<KeyRelease>", lambda _e, idx=i: self.live_edit(idx))
            entry.bind("<FocusOut>", lambda _e, idx=i: self.commit_value(idx))
            entry.bind("<Return>", lambda _e, idx=i: self.commit_value(idx))

            self.entries.append(entry)

            tk.Button(
                content,
                text="×",
                command=lambda idx=i: self.delete_element(idx),
                font=("Sans", 11, "bold"),
                fg="#8b3c3c",
                bg=self.BG,
                activebackground=self.BG,
                activeforeground="#b00000",
                relief="flat",
                cursor="hand2",
            ).grid(row=2, column=col, pady=(1, 0))

        tk.Label(
            self.left,
            text=(
                "Любое валидное изменение сразу перестраивает граф.\n"
                "Узел графа — индекс. Стрелка: i → array[i]."
            ),
            font=("Sans", 10),
            fg=self.MUTED,
            bg=self.BG,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

    def _entries_are_valid(self):
        n = len(self.entries) - 1
        parsed = []

        for entry in self.entries:
            raw = entry.get().strip()
            try:
                value = int(raw)
            except ValueError:
                return False, None

            if not (1 <= value <= n):
                return False, None

            parsed.append(value)

        return True, parsed

    def live_edit(self, index):
        """Перестройка после каждого валидного изменения."""
        if index >= len(self.entries):
            return

        valid, parsed = self._entries_are_valid()

        for entry in self.entries:
            entry.configure(bg=self.ENTRY_BG)

        if not valid:
            self.entries[index].configure(bg=self.INVALID)
            self.graph_status.config(
                text=f"Введите целые числа 1..{len(self.entries) - 1}"
            )
            return

        self.values = parsed
        self.graph_status.config(text="")
        self._render_all(except_array=True)

    def commit_value(self, index):
        if index >= len(self.entries):
            return

        n = len(self.values) - 1
        raw = self.entries[index].get().strip()

        try:
            value = int(raw)
        except ValueError:
            self._restore_entry(index)
            messagebox.showerror(
                "Некорректное значение",
                "Элемент массива должен быть целым числом.",
            )
            return

        if not (1 <= value <= n):
            self._restore_entry(index)
            messagebox.showerror(
                "Значение вне диапазона",
                f"Допустимые значения: от 1 до {n}.",
            )
            return

        self.values[index] = value
        self.entries[index].configure(bg=self.ENTRY_BG)
        self._render_all(except_array=True)

    def _restore_entry(self, index):
        self.entries[index].delete(0, tk.END)
        self.entries[index].insert(0, str(self.values[index]))
        self.entries[index].configure(bg=self.ENTRY_BG)
        self.graph_status.config(text="")
        self._render_all(except_array=True)

    def add_element(self):
        new_n = len(self.values)
        self.values.append(random.randint(1, new_n))
        self._render_array()
        self._render_all(except_array=True)

    def delete_element(self, index):
        if len(self.values) <= 2:
            messagebox.showwarning(
                "Удаление невозможно",
                "В массиве должно оставаться минимум 2 элемента.",
            )
            return

        self.values.pop(index)

        n = len(self.values) - 1
        self.values = [min(max(v, 1), n) for v in self.values]

        self._render_array()
        self._render_all(except_array=True)

    def random_fill(self):
        """
        Классический массив для поиска дубликата:
        [1..n] + один случайный дубликат, затем перемешивание.
        """
        n = len(self.values) - 1
        duplicate = random.randint(1, n)

        self.values = list(range(1, n + 1)) + [duplicate]
        random.shuffle(self.values)

        self._render_array()
        self._render_all(except_array=True)

    def _reachable_tail_cycle(self):
        """
        Идет из 0 по i -> array[i].

        Возвращает:
            tail  — узлы до первого узла цикла;
            cycle — главный цикл, достижимый из 0;
                    cycle[0] — вход в этот цикл.
        """
        seen = {}
        order = []

        current = 0

        while current not in seen:
            seen[current] = len(order)
            order.append(current)
            current = self.values[current]

        cycle_start = seen[current]
        tail = order[:cycle_start]
        cycle = order[cycle_start:]

        return tail, cycle

    def _all_cycles(self):
        """
        Находит ВСЕ циклы функционального графа i -> array[i].

        Возвращает список циклов.
        Каждый цикл — список индексов в порядке обхода.

        Важно:
        - цикл, достижимый из 0, тоже входит в результат;
        - отдельные циклы вроде 5 -> 6 -> 5 больше не теряются.
        """
        n_nodes = len(self.values)

        # 0 = не посещён
        # 1 = находится в текущем DFS-пути
        # 2 = полностью обработан
        state = [0] * n_nodes
        cycles = []

        for start in range(n_nodes):
            if state[start] != 0:
                continue

            current = start
            path = []
            index_in_path = {}

            while state[current] == 0:
                state[current] = 1
                index_in_path[current] = len(path)
                path.append(current)
                current = self.values[current]

            # Попали в вершину текущего пути -> нашли новый цикл.
            if state[current] == 1 and current in index_in_path:
                cycle_start = index_in_path[current]
                cycle = path[cycle_start:]
                cycles.append(cycle)

            # Весь текущий путь теперь обработан.
            for node in path:
                state[node] = 2

        return cycles

    def _strict_duplicate(self):
        """
        Возвращает дубликат только если выполнено строгое условие:
        массив длины n+1 содержит все 1..n,
        ровно одно значение встречается дважды.
        """
        n = len(self.values) - 1
        counts = Counter(self.values)

        if set(counts) != set(range(1, n + 1)):
            return None

        duplicates = [x for x, count in counts.items() if count == 2]

        if len(duplicates) != 1:
            return None

        if any(count not in (1, 2) for count in counts.values()):
            return None

        return duplicates[0]

    def _render_all(self, except_array=False):
        if not except_array:
            self._render_array()

        self._render_mapping()
        self._render_graph()

    def _render_mapping(self):
        self.mapping_canvas.delete("all")

        width = max(self.mapping_canvas.winfo_width(), 270)

        self.mapping_canvas.create_text(
            36,
            20,
            anchor="nw",
            text="Индекс",
            font=("Sans", 11, "bold"),
            fill=self.MUTED,
        )
        self.mapping_canvas.create_text(
            width - 36,
            20,
            anchor="ne",
            text="array[index]",
            font=("Sans", 11, "bold"),
            fill=self.MUTED,
        )

        y = 58

        for i, value in enumerate(self.values):
            self.mapping_canvas.create_text(
                55,
                y,
                text=str(i),
                anchor="e",
                font=("Sans", 17),
                fill=self.TEXT,
            )

            self.mapping_canvas.create_text(
                width / 2,
                y,
                text=">>",
                font=("Sans", 17),
                fill=self.ACCENT,
            )

            self.mapping_canvas.create_text(
                width - 55,
                y,
                text=str(value),
                anchor="w",
                font=("Sans", 17),
                fill=self.TEXT,
            )

            y += 38

        self.mapping_canvas.configure(scrollregion=(0, 0, width, y + 20))

    def _render_graph(self):
        """
        Главный компонент, достижимый из 0:
            хвост слева -> вход -> главный цикл справа.

        Все остальные циклы:
            рисуются отдельно сверху и снизу от главного цикла
            внутри секции "ЦИКЛ".
        """
        if not hasattr(self, "graph_canvas"):
            return

        canvas = self.graph_canvas
        canvas.delete("all")

        if not self.values:
            return

        w = max(canvas.winfo_width(), 500)
        h = max(canvas.winfo_height(), 400)

        tail, main_cycle = self._reachable_tail_cycle()
        entry = main_cycle[0]
        duplicate = self._strict_duplicate()

        all_cycles = self._all_cycles()

        # Главный цикл идентифицируем по множеству его узлов.
        main_cycle_set = set(main_cycle)
        extra_cycles = [
            cycle for cycle in all_cycles
            if set(cycle) != main_cycle_set
        ]

        if duplicate is not None and duplicate == entry:
            subtitle = (
                f"Главный вход в цикл = дубликат {entry}. "
                f"Всего циклов: {len(all_cycles)}"
            )
        elif duplicate is not None:
            subtitle = (
                f"Дубликат массива: {duplicate}; "
                f"вход в главный цикл: {entry}; "
                f"всего циклов: {len(all_cycles)}"
            )
        else:
            subtitle = (
                f"Вход в главный цикл: {entry}; "
                f"всего циклов: {len(all_cycles)}. "
                "Ручной массив может нарушать условие «ровно один дубликат»."
            )

        canvas.create_text(
            18,
            18,
            anchor="nw",
            text=subtitle,
            font=("Sans", 11, "bold"),
            fill=self.TEXT,
        )

        divider_x = max(w * 0.46, 280)

        canvas.create_rectangle(
            14,
            52,
            divider_x - 10,
            h - 20,
            fill=self.TAIL_BG,
            outline="",
        )
        canvas.create_rectangle(
            divider_x + 10,
            52,
            w - 14,
            h - 20,
            fill=self.CYCLE_BG,
            outline="",
        )

        canvas.create_text(
            30,
            68,
            anchor="nw",
            text="ХВОСТ",
            font=("Sans", 12, "bold"),
            fill=self.MUTED,
        )
        canvas.create_text(
            divider_x + 28,
            68,
            anchor="nw",
            text="ЦИКЛЫ",
            font=("Sans", 12, "bold"),
            fill=self.MUTED,
        )

        # -----------------------------
        # 1. Главный остов
        # -----------------------------
        y_mid = h * 0.53
        left_x = 52
        entry_x = divider_x + 6

        tail_nodes = tail[:]
        positions = {}

        # Хвост строго горизонтальный.
        if tail_nodes:
            available = max(entry_x - 125 - left_x, 90)

            if len(tail_nodes) == 1:
                positions[tail_nodes[0]] = (left_x + 30, y_mid)
            else:
                step = available / (len(tail_nodes) - 1)
                for idx, node in enumerate(tail_nodes):
                    positions[node] = (left_x + idx * step, y_mid)

        positions[entry] = (entry_x, y_mid)

        # Главный цикл справа от entry.
        rest_cycle = main_cycle[1:]

        main_cycle_left = divider_x + 105
        main_cycle_right = w - 65
        main_center_x = (main_cycle_left + main_cycle_right) / 2
        main_center_y = y_mid
        main_rx = max((main_cycle_right - main_cycle_left) / 2, 65)

        # Оставляем место сверху/снизу под дополнительные циклы.
        main_ry = min(max(h * 0.13, 55), 95)

        if rest_cycle:
            if len(rest_cycle) == 1:
                positions[rest_cycle[0]] = (
                    main_center_x + main_rx * 0.72,
                    main_center_y,
                )
            else:
                start_angle = math.radians(-145)
                end_angle = math.radians(145)

                for j, node in enumerate(rest_cycle):
                    ratio = j / (len(rest_cycle) - 1)
                    angle = start_angle + (end_angle - start_angle) * ratio

                    positions[node] = (
                        main_center_x + main_rx * math.cos(angle),
                        main_center_y + main_ry * math.sin(angle),
                    )

        # Ребра хвоста.
        path_to_entry = tail_nodes + [entry]
        for a, b in zip(path_to_entry, path_to_entry[1:]):
            self._draw_arrow(canvas, positions[a], positions[b], self.EDGE)

        # Ребра главного цикла.
        if len(main_cycle) == 1:
            self._draw_self_loop(canvas, positions[entry])
        else:
            for a, b in zip(main_cycle, main_cycle[1:]):
                self._draw_arrow(
                    canvas,
                    positions[a],
                    positions[b],
                    self.ACCENT,
                )

            self._draw_curved_return_arrow(
                canvas,
                positions[main_cycle[-1]],
                positions[entry],
                self.ACCENT,
            )

        # Узлы главного остова.
        for node, (x, y) in positions.items():
            self._draw_node(
                canvas,
                x,
                y,
                node,
                is_entry=(node == entry),
            )

        entry_label = (
            f"дубликат / вход: {entry}"
            if duplicate == entry
            else f"главный вход: {entry}"
        )

        canvas.create_text(
            positions[entry][0],
            positions[entry][1] - 58,
            text=entry_label,
            font=("Sans", 10, "bold"),
            fill=self.ACCENT,
        )

        # -----------------------------
        # 2. Дополнительные циклы
        # -----------------------------
        if extra_cycles:
            # Чередуем размещение: верх, низ, верх, низ...
            top_cycles = extra_cycles[0::2]
            bottom_cycles = extra_cycles[1::2]

            cycle_zone_left = divider_x + 55
            cycle_zone_right = w - 45
            zone_width = max(cycle_zone_right - cycle_zone_left, 120)

            self._draw_extra_cycle_row(
                canvas=canvas,
                cycles=top_cycles,
                left=cycle_zone_left,
                right=cycle_zone_right,
                center_y=145,
                label="доп. циклы",
            )

            self._draw_extra_cycle_row(
                canvas=canvas,
                cycles=bottom_cycles,
                left=cycle_zone_left,
                right=cycle_zone_right,
                center_y=h - 125,
                label="",
            )

        # Нижняя строка.
        tail_text = " → ".join(map(str, tail_nodes)) if tail_nodes else "∅"
        main_cycle_text = " → ".join(map(str, main_cycle + [entry]))

        canvas.create_text(
            24,
            h - 34,
            anchor="sw",
            text=(
                f"Главный хвост: {tail_text}    |    "
                f"Главный цикл: {main_cycle_text}    |    "
                f"Доп. циклов: {len(extra_cycles)}"
            ),
            font=("Monospace", 10),
            fill=self.TEXT,
        )

    def _draw_extra_cycle_row(
        self,
        canvas,
        cycles,
        left,
        right,
        center_y,
        label="",
    ):
        """
        Рисует ряд дополнительных циклов в зоне 'ЦИКЛЫ'.

        Каждый цикл — отдельная маленькая замкнутая фигура.
        """
        if not cycles:
            return

        if label:
            canvas.create_text(
                left,
                center_y - 58,
                anchor="w",
                text=label,
                font=("Sans", 9, "bold"),
                fill=self.MUTED,
            )

        total_width = max(right - left, 100)
        slot_width = total_width / len(cycles)

        for i, cycle in enumerate(cycles):
            slot_left = left + i * slot_width
            slot_right = left + (i + 1) * slot_width
            cx = (slot_left + slot_right) / 2

            # Сам цикл делаем компактным.
            rx = min(max(slot_width * 0.28, 42), 75)
            ry = 38

            cycle_positions = {}

            if len(cycle) == 1:
                node = cycle[0]
                cycle_positions[node] = (cx, center_y)

                self._draw_node(
                    canvas,
                    cx,
                    center_y,
                    node,
                    is_entry=False,
                )
                self._draw_self_loop(
                    canvas,
                    (cx, center_y),
                )

            elif len(cycle) == 2:
                a, b = cycle
                cycle_positions[a] = (cx - rx * 0.7, center_y)
                cycle_positions[b] = (cx + rx * 0.7, center_y)

                self._draw_arrow(
                    canvas,
                    cycle_positions[a],
                    cycle_positions[b],
                    self.ACCENT,
                )

                # Обратное ребро отдельной дугой сверху.
                self._draw_upper_return_arrow(
                    canvas,
                    cycle_positions[b],
                    cycle_positions[a],
                    self.ACCENT,
                )

                self._draw_node(
                    canvas,
                    *cycle_positions[a],
                    a,
                    is_entry=False,
                )
                self._draw_node(
                    canvas,
                    *cycle_positions[b],
                    b,
                    is_entry=False,
                )

            else:
                # Узлы равномерно по маленькому эллипсу.
                for j, node in enumerate(cycle):
                    angle = (
                        -math.pi / 2
                        + 2 * math.pi * j / len(cycle)
                    )
                    cycle_positions[node] = (
                        cx + rx * math.cos(angle),
                        center_y + ry * math.sin(angle),
                    )

                for j, node in enumerate(cycle):
                    nxt = cycle[(j + 1) % len(cycle)]
                    self._draw_arrow(
                        canvas,
                        cycle_positions[node],
                        cycle_positions[nxt],
                        self.ACCENT,
                    )

                for node in cycle:
                    self._draw_node(
                        canvas,
                        *cycle_positions[node],
                        node,
                        is_entry=False,
                    )

            cycle_text = " → ".join(map(str, cycle + [cycle[0]]))

            canvas.create_text(
                cx,
                center_y + 62,
                text=cycle_text,
                font=("Monospace", 9),
                fill=self.MUTED,
            )

    def _draw_upper_return_arrow(self, canvas, p1, p2, color):
        """
        Обратная дуга для двухузлового дополнительного цикла:
        A -> B и B -> A.
        """
        x1, y1 = p1
        x2, y2 = p2

        control_x = (x1 + x2) / 2
        control_y = min(y1, y2) - 48

        canvas.create_line(
            x1,
            y1 - self.NODE_RADIUS,
            control_x,
            control_y,
            x2 + self.NODE_RADIUS,
            y2 - 4,
            smooth=True,
            splinesteps=30,
            fill=color,
            width=2.2,
            arrow=tk.LAST,
            arrowshape=(10, 12, 5),
        )

    def _draw_node(self, canvas, x, y, node, is_entry=False):
        r = self.NODE_RADIUS

        canvas.create_oval(
            x - r,
            y - r,
            x + r,
            y + r,
            fill=self.ACCENT_LIGHT if is_entry else self.PANEL,
            outline=self.ACCENT if is_entry else self.TEXT,
            width=4 if is_entry else 2,
        )

        canvas.create_text(
            x,
            y,
            text=str(node),
            font=("Sans", 14, "bold"),
            fill=self.TEXT,
        )

        canvas.create_text(
            x,
            y + 37,
            text=f"[{node}]→{self.values[node]}",
            font=("Monospace", 8),
            fill=self.MUTED,
        )

    def _draw_arrow(self, canvas, p1, p2, color):
        x1, y1 = p1
        x2, y2 = p2

        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)

        if length == 0:
            return

        ux = dx / length
        uy = dy / length
        r = self.NODE_RADIUS + 3

        canvas.create_line(
            x1 + ux * r,
            y1 + uy * r,
            x2 - ux * r,
            y2 - uy * r,
            fill=color,
            width=2.5,
            arrow=tk.LAST,
            arrowshape=(11, 13, 5),
        )

    def _draw_curved_return_arrow(self, canvas, p1, p2, color):
        x1, y1 = p1
        x2, y2 = p2

        control_x = (x1 + x2) / 2
        control_y = max(y1, y2) + 105

        canvas.create_line(
            x1,
            y1 + self.NODE_RADIUS,
            control_x,
            control_y,
            x2 + self.NODE_RADIUS,
            y2 + 8,
            smooth=True,
            splinesteps=36,
            fill=color,
            width=2.5,
            arrow=tk.LAST,
            arrowshape=(11, 13, 5),
        )

    def _draw_self_loop(self, canvas, p):
        x, y = p

        canvas.create_arc(
            x - 36,
            y - 72,
            x + 36,
            y - 10,
            start=30,
            extent=300,
            style=tk.ARC,
            outline=self.ACCENT,
            width=2.5,
        )

        canvas.create_line(
            x + 20,
            y - 16,
            x + 10,
            y - 28,
            fill=self.ACCENT,
            width=2.5,
            arrow=tk.LAST,
        )


if __name__ == "__main__":
    app = ArrayGraphEditor()
    app.mainloop()
