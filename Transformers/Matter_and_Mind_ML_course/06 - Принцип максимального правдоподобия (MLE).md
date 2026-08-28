---
title: "Принцип максимального правдоподобия (MLE)"
course: "Математические основы машинного обучения — Matter and Mind"
lesson: 6
youtube: "https://www.youtube.com/watch?v=SIcJxFgHT9c"
tags:
  - машинное-обучение
  - mle
  - вероятность
---
## Главная идея

Maximum Likelihood Estimation выбирает такие параметры модели $\large \theta$, при которых наблюдаемые данные максимально вероятны.

Пусть:

$$\large
D=\{x_1,\dots,x_n\}
$$

а модель задаёт:

$$\large
p(x|\theta)
$$

Тогда likelihood:

$$\large
L(\theta)=p(D|\theta)
$$

Для независимых наблюдений:

$$\large
L(\theta)=\prod_{i=1}^{n}p(x_i|\theta)
$$

MLE:

$$\large
\boxed{
\theta_{MLE}
=
\arg\max_\theta L(\theta)
}
$$

## Probability vs likelihood

Probability:

```text
θ фиксировано
меняем возможные данные x
```

Likelihood:

```text
данные D фиксированы
меняем параметры θ
```

## Пример с монетой

Пусть вероятность орла равна $\large \theta$.

Если из $\large n$ бросков выпало $\large k$ орлов:

$$\large
L(\theta)
=
\theta^k(1-\theta)^{n-k}
$$

Максимум достигается при:

$$\large
\theta_{MLE}=\frac{k}{n}
$$

То есть MLE даёт наблюдаемую частоту.

## Зачем логарифм

Произведение большого числа вероятностей неудобно.

Так как $\large \log$ монотонен:

$$\large
\arg\max L(\theta)
=
\arg\max \log L(\theta)
$$

Log-likelihood:

$$\large
\ell(\theta)
=
\sum_i\log p(x_i|\theta)
$$

Вместо произведения получили сумму.

## Negative Log-Likelihood

В ML обычно минимизируют loss:

$$\large
NLL(\theta)
=
-\sum_i\log p(x_i|\theta)
$$

Тогда:

$$\large
\arg\max \ell
=
\arg\min NLL
$$

## Связь с cross-entropy и KL

При большой выборке средний NLL приближается к:

$$\large
-\mathbb E_{x\sim P}\log Q_\theta(x)
=
H(P,Q_\theta)
$$

А:

$$\large
H(P,Q_\theta)
=
H(P)+D_{KL}(P\|Q_\theta)
$$

Поэтому:

$$\large
\boxed{
MLE
\Longleftrightarrow
\min_\theta D_{KL}(P\|Q_\theta)
}
$$

Получается единая цепочка:

```text
Likelihood
↓ log
Log-Likelihood
↓ знак минус
NLL
↓
Cross-Entropy
↓
KL divergence
```

## MLE не является алгоритмом оптимизации

MLE отвечает на вопрос:

> какие параметры считать лучшими?

Но не говорит:

> как их найти?

Если параметров миллионы, нужен численный алгоритм оптимизации.

Следующая тема — градиентный спуск.

→ [[07 - Градиентный спуск. Главный алгоритм машинного обучения]]

## Что запомнить

$$\large
\boxed{
\theta_{MLE}
=
\arg\max_\theta
\prod_i p(x_i|\theta)
}
$$

или:

$$\large
\boxed{
\theta_{MLE}
=
\arg\min_\theta
\left[-\sum_i\log p(x_i|\theta)\right]
}
$$

MLE объясняет, почему log-loss и cross-entropy естественно возникают в машинном обучении.
