# Полный workflow работы с HP Ink Tank 310 в Arch Linux

## 0. Исходные данные

Имя очереди CUPS:

```text
Ink_Tank_310
```

Принтер по умолчанию:

```text
Ink_Tank_310
```

Подключение:

```text
USB
```

---

# I. Запуск

## 1. Включить физический принтер

- Включить HP Ink Tank 310.
- Подключить USB-кабель к ноутбуку.
- Убедиться, что в принтере есть бумага.

---

## 2. Проверить, видит ли Linux USB-устройство

```bash
lsusb
```

В списке должен присутствовать HP.

Дополнительная проверка через CUPS:

```bash
lpinfo -v | grep -i hp
```

Должен присутствовать URI вида:

```text
Ink_Tank_310usb://HP/Ink%20Tank%20310%20series...
```

---

## 3. Запустить инфраструктуру CUPS

Для полностью явного запуска:

```bash
sudo systemctl start cups.socket cups.path cups.service
```

Проверить:

```bash
systemctl is-active cups.socket
systemctl is-active cups.path
systemctl is-active cups.service
```

Ожидаемый вывод:

```text
active
active
active
```

Проверить состояние CUPS:

```bash
lpstat -r
```

Ожидается:

```text
scheduler is running
```

---

## 4. Проверить очередь принтера

```bash
lpstat -p Ink_Tank_310 -l
```

Нормальное состояние:

```text
printer Ink_Tank_310 is idle. enabled
```

Значения:

- `idle` — принтер свободен;
- `enabled` — CUPS разрешено отправлять ему задания.

---

## 5. Проверить, принимает ли очередь задания

```bash
lpstat -a Ink_Tank_310
```

Нужно:

```text
Ink_Tank_310 accepting requests
```

Если очередь отключена:

```bash
sudo cupsenable Ink_Tank_310
```

Если не принимает задания:

```bash
sudo cupsaccept Ink_Tank_310
```

---

## 6. Проверить принтер по умолчанию

```bash
lpstat -d
```

Нужно:

```text
system default destination: Ink_Tank_310
```

Если это не так:

```bash
lpoptions -d Ink_Tank_310
```

---

## 7. Общая итоговая проверка перед печатью

```bash
lpstat -t
```

Нужно увидеть:

```text
scheduler is running
system default destination: Ink_Tank_310
Ink_Tank_310 accepting requests
printer Ink_Tank_310 is idle
```

---

# II. Печать

## 8. Печатать документ

Если `Ink_Tank_310` установлен по умолчанию:

```bash
lp ~/Downloads/document.pdf
```

Явный вариант:

```bash
lp -d Ink_Tank_310 ~/Downloads/document.pdf
```

После отправки CUPS вернёт:

```text
request id is Ink_Tank_310-N (1 file(s))
```

Запомнить `Ink_Tank_310-N`, если понадобится отмена.

---

## 9. Несколько копий

```bash
lp -d Ink_Tank_310 -n 2 ~/Downloads/document.pdf
```

---

## 10. Проверить очередь

```bash
lpstat -o
```

Пока документ печатается, задание будет присутствовать в выводе.

После успешного завершения:

```bash
lpstat -o
```

ничего не выводит.

---

## 11. Посмотреть завершённые задания

```bash
lpstat -W completed -o
```

---

## 12. Отменить текущее задание

Посмотреть ID:

```bash
lpstat -o
```

Отменить:

```bash
cancel Ink_Tank_310-N
```

Отменить все задания:

```bash
cancel -a
```

---

# III. Безопасное завершение работы

## 13. Дождаться завершения печати

Первое условие:

```bash
lpstat -o
```

Команда должна вернуть пустой вывод.

Это означает, что активных заданий в очереди нет.

---

## 14. Проверить состояние принтера

```bash
lpstat -p Ink_Tank_310 -l
```

Нужно:

```text
printer Ink_Tank_310 is idle
```

Не отключать USB в момент, когда очередь ещё содержит активное задание.

---

## 15. Проверить, что нет незавершённых заданий

```bash
lpstat -o Ink_Tank_310
```

Пустой вывод = можно завершать инфраструктуру.

---

## 16. Остановить CUPS полностью

Сначала остановить сам демон:

```bash
sudo systemctl stop cups.service
```

Затем отключить точки, которые могут снова автоматически поднять демон:

```bash
sudo systemctl stop cups.socket cups.path
```

Или одной командой:

```bash
sudo systemctl stop cups.service cups.socket cups.path
```

---

## 17. Проверить, что все CUPS units остановлены

```bash
systemctl is-active cups.service
systemctl is-active cups.socket
systemctl is-active cups.path
```

Ожидается:

```text
inactive
inactive
inactive
```

Можно посмотреть всё сразу:

```bash
systemctl status cups.service cups.socket cups.path --no-pager
```

---

## 18. Проверить, что `cupsd` больше не работает

```bash
pgrep -a cupsd
```

Пустой вывод = процесса `cupsd` нет.

---

## 19. Проверить, что IPP TCP socket закрыт

```bash
ss -ltnp | grep ':631'
```

Пустой вывод = TCP listener CUPS на порту 631 отсутствует.

---

## 20. Проверить Unix-сокеты CUPS

```bash
ss -lx | grep -i cups
```

После остановки `cups.socket` и `cups.service` активного listening socket CUPS быть не должно.

---

## 21. Выключить физический принтер

После того как:

```text
lpstat -o
```

пуст,

и CUPS полностью остановлен:

- выключить HP Ink Tank 310;
- отключить USB-кабель.

---

# IV. Полный короткий сценарий

## Запуск

```bash
sudo systemctl start cups.socket cups.path cups.service
systemctl is-active cups.socket cups.path cups.service
lpstat -r
lpstat -d
lpstat -p Ink_Tank_310 -l
lpstat -a Ink_Tank_310
```

---

## Печать

```bash
lp -d Ink_Tank_310 ~/Downloads/document.pdf
```

Следить за очередью:

```bash
lpstat -o
```

---

## Завершение

Дождаться пустой очереди:

```bash
lpstat -o
```

Проверить:

```bash
lpstat -p Ink_Tank_310 -l
```

Остановить CUPS:

```bash
sudo systemctl stop cups.service cups.socket cups.path
```

Проверить:

```bash
systemctl is-active cups.service cups.socket cups.path
pgrep -a cupsd
ss -ltnp | grep ':631'
ss -lx | grep -i cups
```

После этого:

- выключить принтер;
- отключить USB.

---

# V. Если после запуска что-то не работает

## CUPS не работает

```bash
sudo systemctl restart cups.service
```

Проверить:

```bash
systemctl status cups.service --no-pager
```

---

## Принтер disabled

```bash
sudo cupsenable Ink_Tank_310
```

---

## Принтер не принимает задания

```bash
sudo cupsaccept Ink_Tank_310
```

---

## USB не виден

```bash
lsusb
```

```bash
lpinfo -v | grep -i hp
```

---

## Очередь исчезла

Проверить:

```bash
lpstat -p
```

Если `Ink_Tank_310` отсутствует, запустить настройку HP:

```bash
sudo hp-setup -i
```

---

## Проверить лог CUPS

```bash
sudo journalctl -u cups.service -n 100 --no-pager
```

---

# VI. Важное различие: stop и disable

Остановить только текущий запуск:

```bash
sudo systemctl stop cups.service cups.socket cups.path
```

После следующей загрузки systemd units могут снова активироваться, если они включены.

Проверить автозапуск:

```bash
systemctl is-enabled cups.service
systemctl is-enabled cups.socket
systemctl is-enabled cups.path
```

Отключать автозапуск нужно только если я осознанно не хочу, чтобы CUPS автоматически запускался:

```bash
sudo systemctl disable cups.service cups.socket cups.path
```

Вернуть автозапуск:

```bash
sudo systemctl enable cups.socket cups.path
```

Для повседневной работы достаточно `stop`; `disable` каждый раз делать не нужно.

---

# VII. Самая короткая памятка

### Запуск

```bash
sudo systemctl start cups.socket cups.path cups.service
```

### Проверка

```bash
lpstat -t
```

### Печать

```bash
lp -d Ink_Tank_310 file.pdf
```

### Дождаться завершения

```bash
lpstat -o
```

Пустой вывод = заданий нет.

### Полная остановка CUPS

```bash
sudo systemctl stop cups.service cups.socket cups.path
```

### Проверка остановки

```bash
systemctl is-active cups.service cups.socket cups.path
pgrep -a cupsd
ss -ltnp | grep ':631'
ss -lx | grep -i cups
```

### После этого

- выключить принтер;
- отключить USB.
