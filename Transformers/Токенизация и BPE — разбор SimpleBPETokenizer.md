---
title: "Токенизация и BPE — разбор SimpleBPETokenizer"
tags:
  - nlp
  - tokenizer
  - bpe
  - python
  - llm
---

# Токенизация и BPE — разбор `SimpleBPETokenizer`

## 1. Что такое токенизация

Нейросеть не работает непосредственно со строкой:

```text
The fast cat sat near the fat rat.
```

В стандартной языковой модели текст сначала проходит через отдельный компонент — **токенизатор**.

Упрощённый pipeline:

```text
исходный текст
      ↓
нормализация / pre-tokenization
      ↓
разбиение на токены
      ↓
token → token_id
      ↓
Embedding Matrix
      ↓
векторы
      ↓
Transformer
```

Важно различать:

```text
ТЕКСТ
  ↓
ТОКЕНЫ
  ↓
TOKEN IDs
  ↓
EMBEDDING VECTORS
```

**Токен — это ещё не вектор.**

Например, условно:

```text
"The cat"
```

может превратиться в:

```text
["The", " cat"]
```

затем:

```text
[791, 8415]
```

и только после этого ID используются как индексы строк embedding-матрицы:

```text
791  → [ 0.12, -0.81, 0.34, ...]
8415 → [-0.43,  0.17, 0.91, ...]
```

То есть задача tokenizer:

> превратить строку в последовательность дискретных единиц, понятных модели.

---

## 2. Почему нельзя просто разбивать текст по словам

Самый очевидный вариант:

```text
"The cat likes milk"
```

→

```text
["The", "cat", "likes", "milk"]
```

Но тогда vocabulary должен содержать практически все возможные слова.

Возникают проблемы:

```text
cat
cats
Cat
CAT
cat's
categorical
```

Все эти строки могут потребовать отдельных элементов словаря.

Кроме того, всегда появляются новые слова, имена, числа, названия библиотек и т. д.

Если слова нет в vocabulary, пришлось бы использовать что-то вроде:

```text
<UNK>
```

---

## 3. Почему не использовать только отдельные символы

Можно сделать:

```text
cat
```

→

```text
["c", "a", "t"]
```

Плюс такого подхода — маленький базовый vocabulary.

Но последовательность становится намного длиннее.

Для Transformer это существенно: чем больше токенов, тем больше вычислений требуется модели.

Поэтому нужен компромисс между:

```text
целыми словами
```

и:

```text
отдельными символами
```

---

## 4. Subword-токенизация

Современные tokenizer'ы часто работают с **подсловами** — `subwords`.

Например:

```text
unbelievable
```

может быть представлено как:

```text
["un", "believ", "able"]
```

Идея:

```text
частые последовательности
        ↓
делаем крупными токенами

редкие последовательности
        ↓
оставляем разбитыми на более мелкие части
```

Так можно одновременно получить:

- относительно небольшой vocabulary;
- относительно короткие последовательности;
- возможность представлять новые слова.

Один из классических алгоритмов для этого — **BPE**.

---

# 5. Что такое BPE

**BPE — Byte Pair Encoding.**

В NLP его основная идея:

1. Начать с минимальных токенов.
2. Посчитать частоты соседних пар.
3. Найти самую частую пару.
4. Объединить её в новый токен.
5. Повторить процесс много раз.

Например:

```text
cat
cat
cat
catch
```

Изначально:

```text
c a t
c a t
c a t
c a t c h
```

Частая пара:

```text
a + t
```

Создаём новый token:

```text
at
```

Получаем:

```text
c at
c at
c at
c at c h
```

Теперь может оказаться частой пара:

```text
c + at
```

и появится token:

```text
cat
```

Таким образом BPE **сам строит subword vocabulary из статистики корпуса**.

---

# 6. Training и inference tokenizer — разные процессы

Это принципиально важно.

## Training

Во время обучения BPE анализирует большой corpus и строит **merge rules**:

```text
1. a + t → at
2. t + h → th
3. th + e → the
4. the + </w> → the</w>
...
```

## Inference

Когда приходит новый текст, частоты уже не считаются.

Используются ранее сохранённые правила:

```text
новый текст
   ↓
базовые токены
   ↓
merge rule №1
   ↓
merge rule №2
   ↓
...
   ↓
финальные токены
```

Именно это разделение реализовано в `train()` и `tokenize()`.

---

# 7. Что означает `</w>`

В коде каждое слово получает специальный маркер:

```text
</w>
```

Он означает:

```text
end of word
```

Например:

```text
cat
```

представляется как:

```python
("c", "a", "t", "</w>")
```

Это позволяет отличать:

```text
at
```

в середине слова от:

```text
at</w>
```

в конце слова.

То есть BPE может выучить отдельный token:

```text
cat</w>
```

который означает не просто последовательность `cat`, а `cat` именно в конце слова.

---

# 8. Исходный код

Ниже код приведён полностью и без изменений.

```python
from collections import Counter, defaultdict


class SimpleBPETokenizer:
    def __init__(self, num_merges=10):
        self.num_merges = num_merges
        self.merges = []  # Запоминает порядок слияния пар токенов

    def _get_stats(self, words):
        """Считает частоту соседних пар токенов."""
        pairs = defaultdict(int)
        for word, freq in words.items():
            for i in range(len(word) - 1):
                pairs[(word[i], word[i + 1])] += freq
        return pairs

    def _merge_word(self, word, pair):
        """Объединяет найденную пару в один токен внутри слова."""
        new_word = []
        i = 0
        while i < len(word):
            if i < len(word) - 1 and (word[i], word[i + 1]) == pair:
                new_word.append(word[i] + word[i + 1])
                i += 2
            else:
                new_word.append(word[i])
                i += 1
        return tuple(new_word)

    def train(self, text):
        """Обучение: находит самые частые пары и формирует правила слияния."""
        raw_words = text.lower().split()
        # Разбиваем каждое слово на буквы и добавляем конец слова '</w>'
        words = Counter(tuple(list(w) + ['</w>']) for w in raw_words)

        for _ in range(self.num_merges):
            pairs = self._get_stats(words)
            if not pairs:
                break

            best_pair = max(pairs, key=pairs.get)
            if pairs[best_pair] < 2:  # Останавливаемся, если пары слишком редкие
                break

            self.merges.append(best_pair)
            words = {self._merge_word(word, best_pair): freq for word, freq in words.items()}

    def tokenize(self, text):
        """Инференс: применяет выученные правила к новому тексту."""
        raw_words = text.lower().split()
        tokens = []

        for w in raw_words:
            word = tuple(list(w) + ['</w>'])
            for pair in self.merges:
                word = self._merge_word(word, pair)
            tokens.extend(word)

        return tokens


# ==========================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ==========================================

# 1. Обучающий текст (~300 символов)
training_text = """
The cat sat on the mat. Another cat was near the mat. 
The fat cat ate a rat on the mat. The cat likes the mat, 
and the rat likes the cat. A fast cat can catch a rat on the mat.
"""

# 2. Инициализация и обучение (выучить до 12 правил слияния)
tokenizer = SimpleBPETokenizer(num_merges=12)
tokenizer.train(training_text)

print("Выученные правила слияния (по порядку):")
for i, merge in enumerate(tokenizer.merges, 1):
    print(f"{i}. {merge[0]} + {merge[1]} -> {merge[0] + merge[1]}")

print("\n" + "=" * 40 + "\n")

# 3. Токенизация нового текста
input_text = "The fast cat sat near the fat rat wow."
tokens = tokenizer.tokenize(input_text)

print(f"Исходная строка: '{input_text}'")
print(f"Результат токенизации:\n{tokens}")
```

---

# 9. Общая архитектура класса

Класс можно представить так:

```text
SimpleBPETokenizer
│
├── __init__()
│     хранит настройки и merges
│
├── _get_stats()
│     считает частоты соседних пар
│
├── _merge_word()
│     применяет одно конкретное слияние
│
├── train()
│     обучает последовательность merge rules
│
└── tokenize()
      применяет готовые merge rules к новому тексту
```

Главный pipeline:

```text
                    TRAIN

training_text
     ↓
lower() + split()
     ↓
characters + </w>
     ↓
Counter частот слов
     ↓
частоты соседних пар
     ↓
самая частая пара
     ↓
merge
     ↓
повторяем
     ↓
self.merges


                  INFERENCE

input_text
    ↓
lower() + split()
    ↓
characters + </w>
    ↓
self.merges[0]
    ↓
self.merges[1]
    ↓
...
    ↓
готовые токены
```

---

# 10. `Counter` и `defaultdict`

```python
from collections import Counter, defaultdict
```

## `Counter`

`Counter` хранит частоты.

Например:

```python
Counter(["cat", "dog", "cat"])
```

логически даст:

```python
{
    "cat": 2,
    "dog": 1
}
```

В нашем коде ключом является не строка, а текущее токенизированное представление слова.

Например:

```python
("c", "a", "t", "</w>")
```

может иметь частоту:

```text
5
```

То есть нет необходимости хранить пять одинаковых копий слова.

## `defaultdict(int)`

```python
pairs = defaultdict(int)
```

Если ключа ещё нет, его значение автоматически считается равным `0`.

Поэтому можно писать:

```python
pairs[pair] += freq
```

---

# 11. `__init__()`

```python
def __init__(self, num_merges=10):
    self.num_merges = num_merges
    self.merges = []
```

## `num_merges`

Максимальное число правил слияния.

Например:

```python
SimpleBPETokenizer(num_merges=12)
```

означает:

> выучить не более 12 BPE merge rules.

Упрощённо:

```text
мало merges
   ↓
более мелкие токены
   ↓
длиннее последовательность

много merges
   ↓
более крупные токены
   ↓
короче последовательность
```

## `self.merges`

```python
self.merges = []
```

Это главный результат обучения данного класса.

После `train()` там лежит ordered list:

```python
[
    ("a", "t"),
    ("t", "h"),
    ("th", "e"),
    ...
]
```

Порядок обязателен, потому что последующее правило может использовать token, созданный предыдущим правилом.

---

# 12. `_get_stats()`

```python
def _get_stats(self, words):
    pairs = defaultdict(int)

    for word, freq in words.items():
        for i in range(len(word) - 1):
            pairs[(word[i], word[i + 1])] += freq

    return pairs
```

Метод считает частоты **соседних** token pairs.

Пусть:

```python
word = ("c", "a", "t", "</w>")
freq = 5
```

Пары:

```text
("c", "a")
("a", "t")
("t", "</w>")
```

Так как слово встречается пять раз, каждая пара получает `+5`.

Именно поэтому здесь важно `freq`.

---

# 13. `_merge_word()`

Этот метод применяет **одно** правило слияния к **одному** слову.

Например:

```text
word = ("c", "a", "t", "</w>")
pair = ("a", "t")
```

Нужно получить:

```text
("c", "at", "</w>")
```

Ключевая проверка:

```python
(word[i], word[i + 1]) == pair
```

Если соседняя пара совпадает с нужной:

```python
new_word.append(word[i] + word[i + 1])
i += 2
```

То есть:

```text
"a" + "t"
```

становится:

```text
"at"
```

`i += 2` нужен потому, что оба исходных токена уже использованы.

Если совпадения нет:

```python
new_word.append(word[i])
i += 1
```

Текущий token переносится без изменений.

---

# 14. `train()` — подготовка corpus

Первая строка:

```python
raw_words = text.lower().split()
```

Содержит две операции.

## `.lower()`

```text
The
THE
the
```

все становятся:

```text
the
```

Значит регистр полностью теряется.

## `.split()`

Текст делится по whitespace.

Например:

```text
"the cat sat"
```

→

```python
["the", "cat", "sat"]
```

Но punctuation не отделяется.

Поэтому:

```text
mat.
```

остаётся словом `mat.`.

Позже оно превращается в:

```python
("m", "a", "t", ".", "</w>")
```

---

# 15. Начальное представление слов

Строка:

```python
words = Counter(tuple(list(w) + ['</w>']) for w in raw_words)
```

Пошагово для:

```text
cat
```

### `list(w)`

```python
["c", "a", "t"]
```

### Добавляем `</w>`

```python
["c", "a", "t", "</w>"]
```

### Превращаем в tuple

```python
("c", "a", "t", "</w>")
```

### `Counter`

Если `cat` встречается пять раз:

```python
{
    ("c", "a", "t", "</w>"): 5
}
```

То есть BPE начинает обучение с **отдельных Unicode-символов** и маркера конца слова.

---

# 16. Главный цикл BPE

```python
for _ in range(self.num_merges):
```

На каждой итерации:

```text
1. считаем все пары
2. выбираем самую частую
3. сохраняем её
4. объединяем её во всём corpus
5. заново считаем статистику
```

Почему статистику нужно считать снова?

Потому что после merge появляются **новые токены и новые пары**.

Например:

```text
t h e
```

содержит:

```text
t+h
h+e
```

После:

```text
t+h → th
```

получаем:

```text
th e
```

Теперь появилась новая пара:

```text
th + e
```

Её раньше не существовало.

---

# 17. Выбор самой частой пары

```python
best_pair = max(pairs, key=pairs.get)
```

`pairs` логически выглядит как:

```python
{
    ("a", "t"): 18,
    ("t", "h"): 11,
    ("c", "a"): 5,
    ...
}
```

`max(..., key=pairs.get)` возвращает ключ с максимальным значением.

В данном случае:

```python
("a", "t")
```

---

# 18. Условие остановки

```python
if pairs[best_pair] < 2:
    break
```

Если даже самая частая пара встречается только один раз, код прекращает обучение.

Это не обязательная часть математической идеи BPE, а дополнительное решение именно этой учебной реализации.

---

# 19. Сохранение merge rule

```python
self.merges.append(best_pair)
```

Если выбрано:

```python
("a", "t")
```

то это правило фактически означает:

```text
a + t → at
```

После следующей итерации может появиться:

```text
at + </w> → at</w>
```

И так постепенно строятся крупные tokens.

---

# 20. Какие правила реально выучиваются на этом тексте

Для данного `training_text` получаются:

| № | Пара | Частота при выборе | Новый токен |
|---:|---|---:|---|
| 1 | `a` + `t` | 18 | `at` |
| 2 | `t` + `h` | 11 | `th` |
| 3 | `th` + `e` | 11 | `the` |
| 4 | `the` + `</w>` | 10 | `the</w>` |
| 5 | `at` + `</w>` | 10 | `at</w>` |
| 6 | `c` + `at</w>` | 5 | `cat</w>` |
| 7 | `m` + `at` | 5 | `mat` |
| 8 | `.` + `</w>` | 5 | `.</w>` |
| 9 | `n` + `</w>` | 4 | `n</w>` |
| 10 | `mat` + `.</w>` | 4 | `mat.</w>` |
| 11 | `o` + `n</w>` | 3 | `on</w>` |
| 12 | `s` + `</w>` | 3 | `s</w>` |

Именно этот ordered list оказывается в:

```python
self.merges
```

---

# 21. Как появляется `the</w>`

Начало:

```text
t h e </w>
```

После второго merge:

```text
t + h → th
```

получаем:

```text
th e </w>
```

После третьего:

```text
th + e → the
```

получаем:

```text
the </w>
```

После четвёртого:

```text
the + </w> → the</w>
```

получаем:

```text
the</w>
```

Визуально:

```text
t h e </w>
   ↓
th e </w>
   ↓
the </w>
   ↓
the</w>
```

---

# 22. Как появляется `cat</w>`

Начало:

```text
c a t </w>
```

Правило №1:

```text
a + t → at
```

получаем:

```text
c at </w>
```

Правило №5:

```text
at + </w> → at</w>
```

получаем:

```text
c at</w>
```

Правило №6:

```text
c + at</w> → cat</w>
```

получаем:

```text
cat</w>
```

Частое слово постепенно стало единым токеном.

---

# 23. Почему порядок merge rules критичен

Допустим имеются правила:

```text
1. a + t → at
2. at + </w> → at</w>
3. c + at</w> → cat</w>
```

Начальный вид:

```text
c a t </w>
```

Нельзя сначала применить правило №3, потому что token:

```text
at</w>
```

ещё не существует.

Нужно:

```text
c a t </w>
↓
c at </w>
↓
c at</w>
↓
cat</w>
```

Поэтому `self.merges` — именно **упорядоченный список**.

---

# 24. `tokenize()` — inference

Метод:

```python
def tokenize(self, text):
```

не обучает tokenizer.

Он не вызывает `_get_stats()` и не изменяет `self.merges`.

Для каждого слова:

```python
word = tuple(list(w) + ['</w>'])
```

снова создаётся начальное посимвольное представление.

Затем:

```python
for pair in self.merges:
    word = self._merge_word(word, pair)
```

все выученные rules применяются **по порядку**.

---

# 25. Реальный результат `input_text`

Вход:

```text
The fast cat sat near the fat rat wow.
```

Результат:

```python
[
    'the</w>',
    'f', 'a', 's', 't', '</w>',
    'cat</w>',
    's', 'at</w>',
    'n', 'e', 'a', 'r', '</w>',
    'the</w>',
    'f', 'at</w>',
    'r', 'at</w>',
    'w', 'o', 'w', '.</w>'
]
```

Это показывает основную идею subword-tokenization:

```text
частый знакомый фрагмент
        ↓
крупный token

редкий / незнакомый фрагмент
        ↓
несколько маленьких tokens
```

---

# 26. Разбор отдельных слов

## `The`

После `.lower()`:

```text
the
```

Далее:

```text
t h e </w>
↓
th e </w>
↓
the </w>
↓
the</w>
```

Результат — один token:

```text
the</w>
```

## `cat`

```text
c a t </w>
↓
c at </w>
↓
c at</w>
↓
cat</w>
```

Тоже один token.

## `sat`

```text
s a t </w>
↓
s at </w>
↓
s at</w>
```

Полного merge:

```text
s + at</w> → sat</w>
```

не выучено.

Поэтому:

```text
["s", "at</w>"]
```

## `fat`

```text
f a t </w>
↓
f at </w>
↓
f at</w>
```

Результат:

```text
["f", "at</w>"]
```

## `rat`

Аналогично:

```text
["r", "at</w>"]
```

## `near`

Подходящих крупных merge rules почти нет:

```text
["n", "e", "a", "r", "</w>"]
```

## `wow.`

Есть выученное:

```text
. + </w> → .</w>
```

Поэтому:

```text
["w", "o", "w", ".</w>"]
```

---

# 27. Что именно здесь «обучается»

Это не обучение нейронной сети.

Здесь нет:

- weights;
- gradients;
- loss;
- backpropagation;
- optimizer.

Обучение BPE — **статистический алгоритм**.

Его результат:

```python
self.merges
```

То есть выученные параметры данного tokenizer'а — последовательность правил слияния.

---

# 28. Чем этот пример отличается от полноценного LLM-tokenizer

Этот класс хорошо показывает BPE, но production-tokenizer делает больше.

## Нет `token → id`

Сейчас результат:

```python
["the</w>", "cat</w>", ...]
```

Но Transformer обычно получает:

```python
[17, 42, ...]
```

Нужен vocabulary:

```text
"the</w>" → 17
"cat</w>" → 42
```

## Нет `id → token`

Для декодирования нужен обратный словарь:

```text
17 → "the</w>"
42 → "cat</w>"
```

## Нет `decode()`

Полноценный tokenizer умеет:

```text
token IDs
↓
tokens
↓
текст
```

## Нет специальных токенов

Например:

```text
<BOS>
<EOS>
<PAD>
<UNK>
```

или chat-specific markers.

## Нет сложного pre-tokenizer

Здесь только:

```python
lower().split()
```

Реальные tokenizer'ы аккуратно работают с:

- пробелами;
- пунктуацией;
- Unicode;
- числами;
- кодом;
- специальными символами.

---

# 29. Здесь символы, а не bytes

Несмотря на название Byte Pair Encoding, код начинает с:

```python
list(w)
```

То есть с Python Unicode characters.

Например:

```python
list("cat")
```

даёт:

```python
["c", "a", "t"]
```

Byte-level BPE в современных системах может начинать именно с **байтов**.

Это удобно, потому что любой вход можно представить через конечный набор базовых byte symbols.

---

# 30. Почему `.split()` — очень упрощённый pre-tokenizer

Например:

```text
hello world
```

и:

```text
hello     world
```

после `.split()` превращаются в одинаковый список:

```python
["hello", "world"]
```

То есть информация о количестве пробелов уничтожается.

Кроме того:

```text
mat.
```

не разделяется на:

```text
mat
.
```

Поэтому точка участвует в BPE merges вместе с буквами.

Именно поэтому в нашем результате появляются:

```text
.</w>
```

и:

```text
mat.</w>
```

---

# 31. Что происходит с незнакомым словом

Пусть при training не было слова:

```text
wow
```

Tokenizer всё равно начинает с:

```text
w o w </w>
```

и применяет известные merges.

Если подходящих merges нет, слово остаётся мелко разбитым.

Это главное преимущество subword-подхода:

> необязательно знать слово целиком, чтобы разложить его на более мелкие известные единицы.

В данном учебном классе есть нюанс: он возвращает строки напрямую и не имеет фиксированного `token → id` vocabulary. Поэтому даже новый символ просто появляется как строковый token. В настоящей модели вопрос представимости базовых элементов должен быть решён явно.

---

# 32. Vocabulary и количество merges

BPE начинает с некоторого базового vocabulary.

Каждый merge создаёт новый token:

```text
a + t → at
```

добавляет:

```text
at
```

Следующий:

```text
c + at → cat
```

добавляет:

```text
cat
```

Поэтому приблизительно:

\[
|V_{final}| = |V_{base}| + N_{merges}
\]

если каждое правило создаёт новый элемент vocabulary.

Отсюда компромисс:

```text
большой vocabulary
        ↕
короче token sequences

маленький vocabulary
        ↕
длиннее token sequences
```

---

# 33. Почему tokenizer влияет на работу Transformer

Пусть один tokenizer представил текст как:

```text
10 tokens
```

а другой:

```text
18 tokens
```

Для Transformer это разные длины последовательности.

В обычном self-attention строится матрица примерно:

\[
n \times n
\]

где \(n\) — число tokens.

Поэтому слишком дробная токенизация может увеличивать вычислительную стоимость.

Tokenizer также влияет на:

- эффективную длину context window;
- обработку разных языков;
- числа;
- исходный код;
- редкие слова;
- имена;
- стоимость inference, если она считается по токенам.

---

# 34. Связь с embedding matrix

Допустим vocabulary содержит:

\[
V = 50\,000
\]

токенов.

Размер embedding:

\[
d = 768
\]

Тогда:

\[
E \in \mathbb{R}^{50\,000 \times 768}
\]

Tokenizer выдаёт:

```text
token_id = 42
```

Модель выбирает строку:

\[
E_{42}
\]

Получается:

```text
"cat"
  ↓ tokenizer
token_id = 42
  ↓
Embedding Matrix
  ↓
[0.17, -0.52, 0.91, ...]
```

BPE **не создаёт semantic vector**.

Он только решает, какая дискретная единица текста будет использоваться как token.

---

# 35. Training tokenizer и training LLM

Это два разных обучения.

## BPE training

```text
corpus
↓
частоты пар
↓
merge rules
↓
vocabulary
```

Никаких gradients.

## LLM training

```text
corpus
↓
готовый tokenizer
↓
token IDs
↓
neural network
↓
loss
↓
backpropagation
↓
gradients
↓
weights update
```

Обычно tokenizer сначала создаётся отдельно, а затем фиксируется на время обучения основной модели.

---

# 36. Ключевая ментальная модель

Не нужно представлять BPE так, будто во время каждого вызова `tokenize()` он заново ищет наиболее частые пары.

Это происходит только в `train()`.

После training имеется фиксированная таблица:

```text
MERGE RULES

1. a + t        → at
2. t + h        → th
3. th + e       → the
4. the + </w>   → the</w>
5. at + </w>    → at</w>
...
```

Inference:

```text
new text
+
готовые merge rules
=
tokens
```

То есть:

```text
TRAIN:
corpus → statistics → merges

INFERENCE:
text + merges → tokens
```

---

# 37. Весь алгоритм данного класса в нескольких строках

## `train()`

```text
text
↓
lower()
↓
split()
↓
каждое слово → characters + </w>
↓
Counter частот слов
↓
считаем соседние pairs
↓
выбираем самую частую
↓
merge
↓
сохраняем rule
↓
повторяем
```

## `tokenize()`

```text
new text
↓
lower()
↓
split()
↓
characters + </w>
↓
merge №1
↓
merge №2
↓
...
↓
merge №N
↓
tokens
```

---

# 38. Полный pipeline до LLM

```text
TEXT
 ↓
Tokenizer preprocessing
 ↓
BPE / другой subword algorithm
 ↓
TOKENS
 ↓
Vocabulary lookup
 ↓
TOKEN IDs
 ↓
Embedding Matrix
 ↓
TOKEN VECTORS
 ↓
Transformer blocks
 ↓
CONTEXTUAL VECTORS
 ↓
Output projection
 ↓
LOGITS
 ↓
Softmax
 ↓
Probability distribution
 ↓
NEXT TOKEN
```

---

# 39. Что важно запомнить

1. **Токенизация** — преобразование текста в последовательность дискретных токенов.

2. **Token ID** — числовой идентификатор токена в vocabulary.

3. **Embedding** — вектор, который нейросеть связывает с token ID. Это уже следующий этап после tokenizer.

4. **BPE** начинает с маленьких единиц и многократно объединяет самые частые соседние пары.

5. В `train()` пары **ищутся статистически**.

6. В `tokenize()` новые пары уже не ищутся — только применяются ранее сохранённые:

```python
self.merges
```

7. Порядок merges критичен.

8. `</w>` обозначает конец слова и позволяет учитывать положение subword внутри слова.

9. Частые слова и фрагменты постепенно превращаются в крупные tokens.

10. Редкие слова остаются разбитыми на мелкие subwords.

11. Этот класс демонстрирует ядро BPE, но полноценному LLM-tokenizer ещё нужны vocabulary, IDs, decoder, special tokens и более серьёзная обработка входного текста.

---

# Итог

`SimpleBPETokenizer` удобно воспринимать как две отдельные машины.

Первая машина **обучается**:

```text
corpus
↓
частоты соседних последовательностей
↓
self.merges
```

Вторая машина **использует результат обучения**:

```text
новый текст
↓
начальные маленькие токены
↓
self.merges
↓
subword tokens
```

На данном примере хорошо видно, как из отдельных символов:

```text
c a t </w>
```

последовательно получается:

```text
c at </w>
```

затем:

```text
c at</w>
```

и наконец:

```text
cat</w>
```

Именно в этом заключается центральная идея BPE: **частые комбинации постепенно становятся самостоятельными токенами**.
