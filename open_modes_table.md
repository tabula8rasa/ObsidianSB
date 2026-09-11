# Python `open()` — режимы, объекты и свойства

> Таблица сгенерирована автоматически Python-кодом.

> Первые 8 колонок сохранены без изменений.

> `—` означает, что данный атрибут или слой для конкретного типа объекта отсутствует.

## Основная таблица

| mode | f | f.buffer | f.buffer.raw | f.raw | f.readable() | f.writable() | f.seekable() | repr(f) | type(f).__module__ | f.name | f.mode | f.closed | f.encoding | f.errors | f.newlines | f.line_buffering | f.write_through | f.isatty() | f.fileno() | f.tell() | has f.buffer | buffer.closed | buffer.fileno() | buffer.readable() | buffer.writable() | buffer.seekable() | buffer.isatty() | has f.raw | real raw type | raw.name | raw.mode | raw.closed | raw.closefd | raw.fileno() | raw.readable() | raw.writable() | raw.seekable() | raw.isatty() | raw._blksize | file existed before open | file exists after open | size before open | size after open | initial position | base mode | text mode | binary mode | plus mode | logical read | logical write | requires existing | creates if missing | truncates existing | append mode | exclusive create | has read() | has read1() | has readall() | has readinto() | has readinto1() | has readline() | has readlines() | has write() | has writelines() | has seek() | has tell() | has truncate() | has flush() | has close() | has fileno() | has isatty() | has peek() | has detach() | has reconfigure() | public members count | all dir(f) members count | public members | f.closed after close |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| r | TextIOWrapper | BufferedReader | FileIO | — | True | False | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_0.txt' mode='r' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_0.txt | r | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | False | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_0.txt | rb | False | True | 3 | True | False | True | False | 4096 | True | True | 27 | 27 | 0 | r | True | False | False | True | False | True | False | False | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| rb | BufferedReader | — | — | FileIO | True | False | True | <_io.BufferedReader name='/tmp/tmp_ts71ufs/test_1.bin'> | _io | /tmp/tmp_ts71ufs/test_1.bin | rb | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_1.bin | rb | False | True | 3 | True | False | True | False | 4096 | True | True | 27 | 27 | 0 | r | False | True | False | True | False | True | False | False | False | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| rt | TextIOWrapper | BufferedReader | FileIO | — | True | False | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_2.txt' mode='rt' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_2.txt | rt | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | False | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_2.txt | rb | False | True | 3 | True | False | True | False | 4096 | True | True | 27 | 27 | 0 | r | True | False | False | True | False | True | False | False | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| r+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_3.txt' mode='r+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_3.txt | r+ | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_3.txt | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 0 | r | True | False | True | True | True | True | False | False | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| rb+ | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_4.bin'> | _io | /tmp/tmp_ts71ufs/test_4.bin | rb+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_4.bin | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 0 | r | False | True | True | True | True | True | False | False | False | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| r+b | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_5.bin'> | _io | /tmp/tmp_ts71ufs/test_5.bin | rb+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_5.bin | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 0 | r | False | True | True | True | True | True | False | False | False | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| rt+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_6.txt' mode='rt+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_6.txt | rt+ | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_6.txt | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 0 | r | True | False | True | True | True | True | False | False | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| r+t | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_7.txt' mode='r+t' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_7.txt | r+t | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_7.txt | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 0 | r | True | False | True | True | True | True | False | False | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| w | TextIOWrapper | BufferedWriter | FileIO | — | False | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_8.txt' mode='w' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_8.txt | w | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | False | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_8.txt | wb | False | True | 3 | False | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | True | False | False | False | True | False | True | True | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| wb | BufferedWriter | — | — | FileIO | False | True | True | <_io.BufferedWriter name='/tmp/tmp_ts71ufs/test_9.bin'> | _io | /tmp/tmp_ts71ufs/test_9.bin | wb | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_9.bin | wb | False | True | 3 | False | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | False | True | False | False | True | False | True | True | False | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | False | True | False | 23 | 60 | close, closed, detach, fileno, flush, isatty, mode, name, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| wt | TextIOWrapper | BufferedWriter | FileIO | — | False | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_10.txt' mode='wt' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_10.txt | wt | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | False | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_10.txt | wb | False | True | 3 | False | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | True | False | False | False | True | False | True | True | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| w+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_11.txt' mode='w+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_11.txt | w+ | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_11.txt | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | True | False | True | True | True | False | True | True | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| wb+ | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_12.bin'> | _io | /tmp/tmp_ts71ufs/test_12.bin | rb+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_12.bin | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | False | True | True | True | True | False | True | True | False | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| w+b | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_13.bin'> | _io | /tmp/tmp_ts71ufs/test_13.bin | rb+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_13.bin | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | False | True | True | True | True | False | True | True | False | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| wt+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_14.txt' mode='wt+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_14.txt | wt+ | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_14.txt | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | True | False | True | True | True | False | True | True | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| w+t | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_15.txt' mode='w+t' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_15.txt | w+t | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_15.txt | rb+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 0 | 0 | w | True | False | True | True | True | False | True | True | False | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| a | TextIOWrapper | BufferedWriter | FileIO | — | False | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_16.txt' mode='a' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_16.txt | a | False | utf-8 | strict | None | False | False | False | 3 | 27 | True | False | 3 | False | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_16.txt | ab | False | True | 3 | False | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | True | False | False | False | True | False | True | False | True | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| ab | BufferedWriter | — | — | FileIO | False | True | True | <_io.BufferedWriter name='/tmp/tmp_ts71ufs/test_17.bin'> | _io | /tmp/tmp_ts71ufs/test_17.bin | ab | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 27 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_17.bin | ab | False | True | 3 | False | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | False | True | False | False | True | False | True | False | True | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | False | True | False | 23 | 60 | close, closed, detach, fileno, flush, isatty, mode, name, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| at | TextIOWrapper | BufferedWriter | FileIO | — | False | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_18.txt' mode='at' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_18.txt | at | False | utf-8 | strict | None | False | False | False | 3 | 27 | True | False | 3 | False | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_18.txt | ab | False | True | 3 | False | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | True | False | False | False | True | False | True | False | True | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| a+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_19.txt' mode='a+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_19.txt | a+ | False | utf-8 | strict | None | False | False | False | 3 | 27 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_19.txt | ab+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | True | False | True | True | True | False | True | False | True | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| ab+ | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_20.bin'> | _io | /tmp/tmp_ts71ufs/test_20.bin | ab+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 27 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_20.bin | ab+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | False | True | True | True | True | False | True | False | True | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| a+b | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_21.bin'> | _io | /tmp/tmp_ts71ufs/test_21.bin | ab+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 27 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_21.bin | ab+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | False | True | True | True | True | False | True | False | True | False | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| at+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_22.txt' mode='at+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_22.txt | at+ | False | utf-8 | strict | None | False | False | False | 3 | 27 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_22.txt | ab+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | True | False | True | True | True | False | True | False | True | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| a+t | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_23.txt' mode='a+t' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_23.txt | a+t | False | utf-8 | strict | None | False | False | False | 3 | 27 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_23.txt | ab+ | False | True | 3 | True | True | True | False | 4096 | True | True | 27 | 27 | 27 | a | True | False | True | True | True | False | True | False | True | False | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| x | TextIOWrapper | BufferedWriter | FileIO | — | False | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_24.txt' mode='x' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_24.txt | x | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | False | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_24.txt | xb | False | True | 3 | False | True | True | False | 4096 | False | True | None | 0 | 0 | x | True | False | False | False | True | False | True | False | False | True | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| xb | BufferedWriter | — | — | FileIO | False | True | True | <_io.BufferedWriter name='/tmp/tmp_ts71ufs/test_25.bin'> | _io | /tmp/tmp_ts71ufs/test_25.bin | xb | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_25.bin | xb | False | True | 3 | False | True | True | False | 4096 | False | True | None | 0 | 0 | x | False | True | False | False | True | False | True | False | False | True | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | False | True | False | 23 | 60 | close, closed, detach, fileno, flush, isatty, mode, name, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| xt | TextIOWrapper | BufferedWriter | FileIO | — | False | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_26.txt' mode='xt' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_26.txt | xt | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | False | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_26.txt | xb | False | True | 3 | False | True | True | False | 4096 | False | True | None | 0 | 0 | x | True | False | False | False | True | False | True | False | False | True | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| x+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_27.txt' mode='x+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_27.txt | x+ | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_27.txt | xb+ | False | True | 3 | True | True | True | False | 4096 | False | True | None | 0 | 0 | x | True | False | True | True | True | False | True | False | False | True | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| xb+ | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_28.bin'> | _io | /tmp/tmp_ts71ufs/test_28.bin | xb+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_28.bin | xb+ | False | True | 3 | True | True | True | False | 4096 | False | True | None | 0 | 0 | x | False | True | True | True | True | False | True | False | False | True | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| x+b | BufferedRandom | — | — | FileIO | True | True | True | <_io.BufferedRandom name='/tmp/tmp_ts71ufs/test_29.bin'> | _io | /tmp/tmp_ts71ufs/test_29.bin | xb+ | False | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | ERROR: AttributeError | False | 3 | 0 | False | — | — | — | — | — | — | True | FileIO | /tmp/tmp_ts71ufs/test_29.bin | xb+ | False | True | 3 | True | True | True | False | 4096 | False | True | None | 0 | 0 | x | False | True | True | True | True | False | True | False | False | True | True | True | False | True | True | True | True | True | True | True | True | True | True | True | True | True | True | True | False | 24 | 61 | close, closed, detach, fileno, flush, isatty, mode, name, peek, raw, read, read1, readable, readinto, readinto1, readline, readlines, seek, seekable, tell, truncate, writable, write, writelines | True |
| xt+ | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_30.txt' mode='xt+' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_30.txt | xt+ | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_30.txt | xb+ | False | True | 3 | True | True | True | False | 4096 | False | True | None | 0 | 0 | x | True | False | True | True | True | False | True | False | False | True | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |
| x+t | TextIOWrapper | BufferedRandom | FileIO | — | True | True | True | <_io.TextIOWrapper name='/tmp/tmp_ts71ufs/test_31.txt' mode='x+t' encoding='utf-8'> | _io | /tmp/tmp_ts71ufs/test_31.txt | x+t | False | utf-8 | strict | None | False | False | False | 3 | 0 | True | False | 3 | True | True | True | False | False | FileIO | /tmp/tmp_ts71ufs/test_31.txt | xb+ | False | True | 3 | True | True | True | False | 4096 | False | True | None | 0 | 0 | x | True | False | True | True | True | False | True | False | False | True | True | False | False | False | False | True | True | True | True | True | True | True | True | True | True | True | False | True | True | 26 | 63 | buffer, close, closed, detach, encoding, errors, fileno, flush, isatty, line_buffering, mode, name, newlines, read, readable, readline, readlines, reconfigure, seek, seekable, tell, truncate, writable, write, write_through, writelines | True |

---

# API объектов, возвращаемых `open()`

Ниже перечислены публичные атрибуты и методы каждого класса, встретившегося при тестировании.

## `_io.BufferedRandom`

### Атрибуты

- `closed`
- `mode`
- `name`
- `raw`

### Методы

- `close()`
- `detach()`
- `fileno()`
- `flush()`
- `isatty()`
- `peek()`
- `read()`
- `read1()`
- `readable()`
- `readinto()`
- `readinto1()`
- `readline()`
- `readlines()`
- `seek()`
- `seekable()`
- `tell()`
- `truncate()`
- `writable()`
- `write()`
- `writelines()`

### Все публичные members

```text
close
closed
detach
fileno
flush
isatty
mode
name
peek
raw
read
read1
readable
readinto
readinto1
readline
readlines
seek
seekable
tell
truncate
writable
write
writelines
```

## `_io.BufferedReader`

### Атрибуты

- `closed`
- `mode`
- `name`
- `raw`

### Методы

- `close()`
- `detach()`
- `fileno()`
- `flush()`
- `isatty()`
- `peek()`
- `read()`
- `read1()`
- `readable()`
- `readinto()`
- `readinto1()`
- `readline()`
- `readlines()`
- `seek()`
- `seekable()`
- `tell()`
- `truncate()`
- `writable()`
- `write()`
- `writelines()`

### Все публичные members

```text
close
closed
detach
fileno
flush
isatty
mode
name
peek
raw
read
read1
readable
readinto
readinto1
readline
readlines
seek
seekable
tell
truncate
writable
write
writelines
```

## `_io.BufferedWriter`

### Атрибуты

- `closed`
- `mode`
- `name`
- `raw`

### Методы

- `close()`
- `detach()`
- `fileno()`
- `flush()`
- `isatty()`
- `read()`
- `read1()`
- `readable()`
- `readinto()`
- `readinto1()`
- `readline()`
- `readlines()`
- `seek()`
- `seekable()`
- `tell()`
- `truncate()`
- `writable()`
- `write()`
- `writelines()`

### Все публичные members

```text
close
closed
detach
fileno
flush
isatty
mode
name
raw
read
read1
readable
readinto
readinto1
readline
readlines
seek
seekable
tell
truncate
writable
write
writelines
```

## `_io.FileIO`

### Атрибуты

- `closed`
- `closefd`
- `mode`
- `name`

### Методы

- `close()`
- `fileno()`
- `flush()`
- `isatty()`
- `read()`
- `readable()`
- `readall()`
- `readinto()`
- `readline()`
- `readlines()`
- `seek()`
- `seekable()`
- `tell()`
- `truncate()`
- `writable()`
- `write()`
- `writelines()`

### Все публичные members

```text
close
closed
closefd
fileno
flush
isatty
mode
name
read
readable
readall
readinto
readline
readlines
seek
seekable
tell
truncate
writable
write
writelines
```

## `_io.TextIOWrapper`

### Атрибуты

- `buffer`
- `closed`
- `encoding`
- `errors`
- `line_buffering`
- `mode`
- `name`
- `newlines`
- `write_through`

### Методы

- `close()`
- `detach()`
- `fileno()`
- `flush()`
- `isatty()`
- `read()`
- `readable()`
- `readline()`
- `readlines()`
- `reconfigure()`
- `seek()`
- `seekable()`
- `tell()`
- `truncate()`
- `writable()`
- `write()`
- `writelines()`

### Все публичные members

```text
buffer
close
closed
detach
encoding
errors
fileno
flush
isatty
line_buffering
mode
name
newlines
read
readable
readline
readlines
reconfigure
seek
seekable
tell
truncate
writable
write
write_through
writelines
```
