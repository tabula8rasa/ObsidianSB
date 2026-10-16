---
title: "Токенизация и BPE — разбор SimpleBPETokenizer"
tags:
  - nlp
  - tokenizer
  - bpe
  - python
  - llm
---
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

## 5. Что такое BPE

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

## 6. Training и inference tokenizer — разные процессы

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

## 7. Что означает `</w>`

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

## 8. Исходный код

Ниже код приведён полностью и без изменений.

```python
from collections import Counter, defaultdict


class SimpleBPETokenizer:
    def __init__(self, num_merges=10):
        self.num_merges = num_merges
        self.merges = []  # Запоминает порядок слияния пар токенов
        self.token2id = {}   # NEW: токен -> id
        self.id2token = {}   # NEW: id -> токен

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
        raw_words = text.lower().split()
        words = Counter(tuple(list(w) + ['</w>']) for w in raw_words)

        for _ in range(self.num_merges):
            pairs = self._get_stats(words)
            if not pairs:
                break

            best_pair = max(pairs, key=pairs.get)
            if pairs[best_pair] < 2:
                break

            self.merges.append(best_pair)
            words = {self._merge_word(word, best_pair): freq for word, freq in words.items()}

        # NEW: строим словарь из всех токенов, оставшихся после слияний
        vocab = {'<unk>'}  # спецтокен для неизвестных символов
        for word in words:
            vocab.update(word)
        self.token2id = {tok: i for i, tok in enumerate(sorted(vocab))}
        self.id2token = {i: tok for tok, i in self.token2id.items()}

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
        
    # NEW: токены -> id
    def encode(self, text):
        unk = self.token2id['<unk>']
        return [self.token2id.get(tok, unk) for tok in self.tokenize(text)]

    # NEW: id -> токены
    def decode(self, ids):
        return [self.id2token[i] for i in ids]


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
input_text = "The fast cat sat near the fat rat wow z."
tokens = tokenizer.tokenize(input_text)

print(f"Исходная строка: '{input_text}'")
print(f"Результат токенизации:\n{tokens}")


ids = tokenizer.encode(input_text)
print("ID:", ids)
print("Обратно:", tokenizer.decode(ids))
```
