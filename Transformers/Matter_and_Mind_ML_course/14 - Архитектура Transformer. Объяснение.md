---
title: "Архитектура Transformer. Объяснение"
course: "Математические основы машинного обучения — Matter and Mind"
lesson: 14
youtube: "https://www.youtube.com/watch?v=ueh2Ih0uKnI"
tags:
  - машинное-обучение
  - transformer
  - llm
---

# Архитектура Transformer. Объяснение

> Видео: https://www.youtube.com/watch?v=ueh2Ih0uKnI

> Формат: смысловой учебный конспект, а не дословная стенограмма.
## Главная идея

Transformer собирает почти все темы курса в одну архитектуру:

- embeddings;
- Softmax;
- Self-Attention;
- MLP;
- cross-entropy;
- backpropagation;
- gradient descent.

Классический Transformer состоит из:

```text
Encoder
Decoder
```

## Путь входа

```text
Текст
 ↓
Tokenizer
 ↓
Token IDs
 ↓
Embeddings
 ↓
+ positional information
 ↓
Transformer blocks
 ↓
Contextual representations
```

## Зачем позиции

Self-attention сам по себе не знает порядок токенов.

Поэтому к embeddings добавляется positional information.

В классическом Transformer использовались sinusoidal positional encodings; в современных LLM часто применяются другие методы, например RoPE.

## Encoder block

Упрощённо:

```text
Input
 ↓
Multi-Head Self-Attention
 ↓
Residual + Norm
 ↓
MLP
 ↓
Residual + Norm
 ↓
Output
```

Attention смешивает контекст между токенами.

MLP нелинейно преобразует representation каждого токена.

## Residual connection

Вместо только:

\[
F(x)
\]

используется:

\[
x+F(x)
\]

Это улучшает прохождение информации и gradients через глубокую сеть.

## Decoder

Классический decoder:

1. masked self-attention;
2. cross-attention к encoder;
3. MLP.

```text
previous output tokens
        ↓
Masked Self-Attention
        ↓
Cross-Attention ← Encoder output
        ↓
MLP
        ↓
next-token logits
```

## Causal mask

При генерации token на позиции \(t\) не должен использовать будущие токены.

Поэтому:

```text
token 1 → видит 1
token 2 → видит 1,2
token 3 → видит 1,2,3
```

## Cross-attention

В cross-attention:

- Query — из decoder;
- Key и Value — из encoder.

Decoder как бы спрашивает encoder:

> какая часть входа сейчас нужна для генерации следующего токена?

## Авторегрессионная генерация

Модель генерирует токены по одному:

```text
context
 ↓
logits
 ↓
softmax
 ↓
next token
 ↓
добавляем его в context
 ↓
повторяем
```

Математически:

\[
p(x_{t+1}|x_{\le t})
\]

## GPT

GPT — decoder-only Transformer.

Отдельного encoder нет.

```text
tokens
 ↓
masked Transformer blocks
 ↓
logits
 ↓
next token
```

Такой дизайн удобен для языкового моделирования.

## Другие варианты

### Encoder-only

Полезен для:

- классификации;
- embeddings;
- понимания текста.

### Encoder-decoder

Полезен для sequence-to-sequence:

- перевод;
- summarization.

### Decoder-only

Полезен для autoregressive generation и используется во многих современных LLM.

## Обучение

Для следующего токена:

\[
L_t
=
-\log p_\theta(x_t|x_{<t})
\]

Для последовательности:

\[
L
=
-\sum_t
\log p_\theta(x_t|x_{<t})
\]

Дальше:

```text
Cross-Entropy
 ↓
Backpropagation
 ↓
Gradients
 ↓
Optimizer
 ↓
Parameter update
```

## Как весь курс собирается вместе

```text
Информация
  ↓
Энтропия
  ↓
Cross-Entropy / KL / Mutual Information
  ↓
MLE
  ↓
Gradient Descent
  ↓
Logistic Regression
  ↓
Backpropagation
  ↓
Softmax
  ↓
Embeddings
  ↓
MLP
  ↓
Self-Attention
  ↓
Transformer
```

## Мультимодальность

Если изображения, аудио или видео превратить в последовательности vectors/tokens, Transformer может работать и с ними.

Например изображение можно разбить на patches и представить каждый patch вектором.

## Главная мысль

Современный Transformer состоит из относительно простых математических операций:

- matrix multiplication;
- dot product;
- normalization;
- nonlinear activation;
- probability distributions;
- gradients.

Сложность возникает из их масштабного многократного соединения.

## Что запомнить

Современная decoder-only LLM в упрощённом виде:

```text
Tokens
 ↓
Embeddings + Position
 ↓
[Masked Attention + MLP] × N
 ↓
Logits
 ↓
Softmax
 ↓
Next token
```

Transformer многократно чередует:

\[
\boxed{\text{обмен контекстом через Attention}}
\]

и:

\[
\boxed{\text{нелинейную обработку через MLP}}
\]
