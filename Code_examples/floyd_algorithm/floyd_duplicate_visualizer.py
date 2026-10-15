import math
import tkinter as tk
from tkinter import ttk, messagebox

DEFAULT_NUMS = [1, 3, 4, 2, 2]


def parse_nums(text: str) -> list[int]:
    text = text.strip().replace('[', '').replace(']', '')
    if not text:
        raise ValueError('Список пуст.')

    nums = [int(part.strip()) for part in text.split(',')]

    if len(nums) < 2:
        raise ValueError('Нужно минимум два элемента.')

    max_allowed = len(nums) - 1
    if any(x < 1 or x > max_allowed for x in nums):
        raise ValueError(
            f'Для классической задачи значения должны быть в диапазоне 1..{max_allowed}.'
        )

    return nums


def build_steps(nums: list[int]) -> list[dict]:
    steps = []

    slow = nums[0]
    fast = nums[0]

    steps.append({
        'phase': 0,
        'title': 'Инициализация',
        'slow': slow,
        'fast': fast,
        'slow_edges': [],
        'fast_edges': [],
        'text': (
            f'slow = nums[0] = {slow}\n'
            f'fast = nums[0] = {fast}\n\n'
            'Далее slow идёт на 1 ребро, fast — на 2.'
        ),
    })

    iteration = 1
    while True:
        old_slow = slow
        old_fast = fast

        slow = nums[old_slow]
        fast_mid = nums[old_fast]
        fast = nums[fast_mid]

        steps.append({
            'phase': 1,
            'title': f'Фаза 1 — поиск встречи, шаг {iteration}',
            'slow': slow,
            'fast': fast,
            'slow_edges': [(old_slow, slow)],
            'fast_edges': [(old_fast, fast_mid), (fast_mid, fast)],
            'text': (
                f'slow: {old_slow} → {slow}\n'
                f'fast: {old_fast} → {fast_mid} → {fast}\n\n'
                + ('Указатели встретились внутри цикла.' if slow == fast
                   else 'Указатели пока находятся в разных узлах.')
            ),
        })

        if slow == fast:
            break
        iteration += 1

    meeting = slow
    slow = nums[0]

    steps.append({
        'phase': 2,
        'title': 'Фаза 2 — возвращаем slow в начало',
        'slow': slow,
        'fast': fast,
        'slow_edges': [],
        'fast_edges': [],
        'text': (
            f'Точка встречи первой фазы: {meeting}\n'
            f'slow снова ставим в nums[0] = {slow}\n'
            f'fast остаётся в {fast}\n\n'
            'Теперь оба указателя двигаются по одному ребру.'
        ),
    })

    iteration = 1
    while slow != fast:
        old_slow = slow
        old_fast = fast

        slow = nums[slow]
        fast = nums[fast]

        steps.append({
            'phase': 2,
            'title': f'Фаза 2 — поиск входа в цикл, шаг {iteration}',
            'slow': slow,
            'fast': fast,
            'slow_edges': [(old_slow, slow)],
            'fast_edges': [(old_fast, fast)],
            'text': (
                f'slow: {old_slow} → {slow}\n'
                f'fast: {old_fast} → {fast}\n\n'
                + (f'Указатели встретились в {slow}. Это дубликат.' if slow == fast
                   else 'Продолжаем двигать оба указателя на 1 ребро.')
            ),
        })
        iteration += 1

    steps.append({
        'phase': 3,
        'title': 'Готово',
        'slow': slow,
        'fast': fast,
        'slow_edges': [],
        'fast_edges': [],
        'text': (
            f'Дубликат = {slow}\n\n'
            f'Значение {slow} встречается {nums.count(slow)} раз(а).\n'
            'В графе это вход в цикл.'
        ),
    })

    return steps


class FloydVisualizer(tk.Tk):
    BG = '#f7f7f3'
    PANEL = '#ffffff'
    TEXT = '#202520'
    MUTED = '#6f766f'
    EDGE = '#a8aea8'
    NODE_FILL = '#ecebdc'
    NODE_OUTLINE = '#303630'
    SLOW = '#c94b45'
    FAST = '#3f6fb6'
    ACTIVE = '#d9e0cf'

    def __init__(self):
        super().__init__()
        self.title('Алгоритм Флойда — поиск дубликата')
        self.geometry('1180x820')
        self.minsize(980, 700)
        self.configure(bg=self.BG)

        self.nums = DEFAULT_NUMS[:]
        self.steps = build_steps(self.nums)
        self.step_index = 0
        self.node_positions = {}

        self._build_ui()
        self._render()

        self.bind('<Right>', lambda _e: self.next_step())
        self.bind('<Left>', lambda _e: self.prev_step())

    def _build_ui(self):
        top = tk.Frame(self, bg=self.BG)
        top.pack(fill='x', padx=24, pady=(20, 10))

        tk.Label(
            top,
            text='Алгоритм Флойда: интерактивная визуализация',
            font=('Sans', 20, 'bold'),
            fg=self.TEXT,
            bg=self.BG,
        ).pack(anchor='w')

        tk.Label(
            top,
            text='Узел = индекс i, стрелка = i → nums[i]. Красный — slow, синий — fast.',
            font=('Sans', 11),
            fg=self.MUTED,
            bg=self.BG,
        ).pack(anchor='w', pady=(4, 12))

        row = tk.Frame(top, bg=self.BG)
        row.pack(fill='x')

        tk.Label(row, text='Список:', font=('Sans', 11, 'bold'), fg=self.TEXT, bg=self.BG).pack(side='left')

        self.entry = tk.Entry(row, font=('Monospace', 12), relief='solid', bd=1)
        self.entry.pack(side='left', fill='x', expand=True, padx=10)
        self.entry.insert(0, ', '.join(map(str, self.nums)))

        ttk.Button(row, text='Построить', command=self.rebuild).pack(side='left')

        body = tk.Frame(self, bg=self.BG)
        body.pack(fill='both', expand=True, padx=24, pady=10)

        graph_frame = tk.Frame(body, bg=self.PANEL, bd=1, relief='solid')
        graph_frame.pack(side='left', fill='both', expand=True)

        self.canvas = tk.Canvas(graph_frame, bg=self.PANEL, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda _e: self._render())

        side = tk.Frame(body, bg=self.BG, width=330)
        side.pack(side='left', fill='y', padx=(16, 0))
        side.pack_propagate(False)

        self.phase_label = tk.Label(
            side, text='', wraplength=300, justify='left', anchor='w',
            font=('Sans', 15, 'bold'), fg=self.TEXT, bg=self.BG,
        )
        self.phase_label.pack(fill='x', pady=(4, 12))

        self.info = tk.Label(
            side, text='', wraplength=300, justify='left', anchor='nw',
            font=('Monospace', 11), fg=self.TEXT, bg=self.BG,
        )
        self.info.pack(fill='x')

        self.position_label = tk.Label(side, text='', font=('Sans', 10), fg=self.MUTED, bg=self.BG)
        self.position_label.pack(anchor='w', pady=(20, 6))

        nav = tk.Frame(side, bg=self.BG)
        nav.pack(fill='x')

        self.prev_button = ttk.Button(nav, text='← Назад', command=self.prev_step)
        self.prev_button.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.next_button = ttk.Button(nav, text='Далее →', command=self.next_step)
        self.next_button.pack(side='left', fill='x', expand=True, padx=(5, 0))

        ttk.Button(side, text='Сбросить на начало', command=self.reset_steps).pack(fill='x', pady=(10, 0))

        tk.Label(side, text='● slow', fg=self.SLOW, bg=self.BG, font=('Sans', 11, 'bold')).pack(anchor='w', pady=(25, 0))
        tk.Label(side, text='● fast', fg=self.FAST, bg=self.BG, font=('Sans', 11, 'bold')).pack(anchor='w', pady=(4, 0))

        tk.Label(
            side, text='Клавиши:\n→ следующий шаг\n← предыдущий шаг',
            justify='left', fg=self.MUTED, bg=self.BG, font=('Sans', 10),
        ).pack(anchor='w', pady=(24, 0))

    def rebuild(self):
        try:
            self.nums = parse_nums(self.entry.get())
            self.steps = build_steps(self.nums)
        except Exception as exc:
            messagebox.showerror('Ошибка списка', str(exc))
            return
        self.step_index = 0
        self._render()

    def reset_steps(self):
        self.step_index = 0
        self._render()

    def next_step(self):
        if self.step_index < len(self.steps) - 1:
            self.step_index += 1
            self._render()

    def prev_step(self):
        if self.step_index > 0:
            self.step_index -= 1
            self._render()

    def _render(self):
        if not hasattr(self, 'canvas'):
            return

        state = self.steps[self.step_index]
        self.phase_label.config(text=state['title'])
        self.info.config(text=state['text'])
        self.position_label.config(text=f'Шаг {self.step_index + 1} из {len(self.steps)}')

        self.prev_button.config(state='normal' if self.step_index > 0 else 'disabled')
        self.next_button.config(state='normal' if self.step_index < len(self.steps) - 1 else 'disabled')

        self._draw_graph(state)

    def _layout_nodes(self):
        w = max(self.canvas.winfo_width(), 600)
        h = max(self.canvas.winfo_height(), 500)
        count = len(self.nums)
        cx, cy = w / 2, h / 2
        radius = min(w, h) * (0.30 if count <= 7 else 0.36)

        self.node_positions = {}
        for i in range(count):
            angle = -math.pi / 2 + 2 * math.pi * i / count
            self.node_positions[i] = (
                cx + radius * math.cos(angle),
                cy + radius * math.sin(angle),
            )

    def _draw_graph(self, state):
        self.canvas.delete('all')
        self._layout_nodes()

        self.canvas.create_text(18, 16, anchor='nw', text=f'nums = {self.nums}', fill=self.TEXT, font=('Monospace', 13, 'bold'))
        self.canvas.create_text(18, 44, anchor='nw', text='Каждая стрелка: i → nums[i]', fill=self.MUTED, font=('Sans', 10))

        for src, dst in enumerate(self.nums):
            self._draw_edge(src, dst, self.EDGE, 2)

        for src, dst in state['slow_edges']:
            self._draw_edge(src, dst, self.SLOW, 5)

        for src, dst in state['fast_edges']:
            self._draw_edge(src, dst, self.FAST, 4)

        for i, (x, y) in self.node_positions.items():
            active = i in (state['slow'], state['fast'])
            fill = self.ACTIVE if active else self.NODE_FILL
            r = 34
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline=self.NODE_OUTLINE, width=2)
            self.canvas.create_text(x, y-6, text=str(i), fill=self.TEXT, font=('Sans', 16, 'bold'))
            self.canvas.create_text(x, y+15, text=f'→ {self.nums[i]}', fill=self.MUTED, font=('Monospace', 9))

        slow, fast = state['slow'], state['fast']

        if slow == fast:
            x, y = self.node_positions[slow]
            self.canvas.create_oval(x-42, y-42, x+42, y+42, outline=self.SLOW, width=4)
            self.canvas.create_oval(x-48, y-48, x+48, y+48, outline=self.FAST, width=4)
            self.canvas.create_text(x, y-58, text='slow + fast', fill=self.TEXT, font=('Sans', 10, 'bold'))
        else:
            self._draw_pointer_marker(slow, 'slow', self.SLOW, -1)
            self._draw_pointer_marker(fast, 'fast', self.FAST, +1)

        if state['phase'] == 3:
            self.canvas.create_text(
                self.canvas.winfo_width()/2,
                self.canvas.winfo_height()-42,
                text=f"Дубликат: {state['slow']}",
                fill=self.TEXT,
                font=('Sans', 17, 'bold'),
            )

    def _draw_pointer_marker(self, node, label, color, side):
        x, y = self.node_positions[node]
        marker_x = x + 54 * side
        marker_y = y - 52
        self.canvas.create_line(marker_x, marker_y+14, x+22*side, y-22, fill=color, width=3, arrow=tk.LAST)
        self.canvas.create_text(marker_x, marker_y, text=label, fill=color, font=('Sans', 11, 'bold'))

    def _draw_edge(self, src, dst, color, width):
        x1, y1 = self.node_positions[src]
        x2, y2 = self.node_positions[dst]
        node_r = 36

        if src == dst:
            loop_r = 34
            self.canvas.create_arc(x1-loop_r, y1-72, x1+loop_r, y1-10, start=25, extent=300, style=tk.ARC, outline=color, width=width)
            self.canvas.create_line(x1+21, y1-17, x1+12, y1-29, fill=color, width=width, arrow=tk.LAST)
            return

        dx, dy = x2-x1, y2-y1
        length = math.hypot(dx, dy)
        ux, uy = dx/length, dy/length

        start_x = x1 + ux * node_r
        start_y = y1 + uy * node_r
        end_x = x2 - ux * (node_r + 5)
        end_y = y2 - uy * (node_r + 5)

        self.canvas.create_line(
            start_x, start_y, end_x, end_y,
            fill=color, width=width, arrow=tk.LAST,
            arrowshape=(10, 12, 5),
        )


if __name__ == '__main__':
    FloydVisualizer().mainloop()
