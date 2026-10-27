
import os # Проверка наличия файла и его размера
import heapq # Помогает строить дерево Хаффмана, выбирая узлы с наименьшей частотой
import struct # Записывает числа в архив в двоичном формате
import subprocess # Запуск системной команды diff для сравнения файлов
from collections import Counter # Подсчитывает количество вхождений каждого символа


# 1. Преобразование BWT (Барроуза — Уилера)
def bwt_transform(data):

    # Добавляем уникальный символ конца, который не встречается среди байтов
    text = list(data) + [256]
    n = len(text)

    # Создаём начальный порядок символов
    order = sorted(range(n), key=lambda i: text[i])
    classes = [0] * n

    for i in range(1, n):
        classes[order[i]] = classes[order[i - 1]]

        if text[order[i]] != text[order[i - 1]]:
            classes[order[i]] += 1

    # Сортируем циклические сдвиги, постепенно увеличивая сравниваемую длину
    length = 1

    while length < n:
        order = [(i - length) % n for i in order]
        order.sort(key=lambda i: classes[i])

        new_classes = [0] * n

        for i in range(1, n):
            current = order[i]
            previous = order[i - 1]

            current_pair = (
                classes[current],
                classes[(current + length) % n]
            )

            previous_pair = (
                classes[previous],
                classes[(previous + length) % n]
            )

            new_classes[current] = new_classes[previous]

            if current_pair != previous_pair:
                new_classes[current] += 1

        classes = new_classes
        length *= 2

    # Получаем последний столбец отсортированных циклических сдвигов
    last_column = [
        text[(i - 1) % n]
        for i in order
    ]

    # Запоминаем позицию исходного текста
    primary_index = order.index(0)

    # Запоминаем позицию специального символа конца
    sentinel_position = last_column.index(256)

    # Убираем специальный символ, так как он не помещается в один байт
    transformed = bytes(
        char for char in last_column if char != 256
    )

    return transformed, sentinel_position, primary_index


# 2. Обратное преобразование BWT
def inverse_bwt(transformed, sentinel_position, primary_index):

    # Возвращаем специальный символ конца на прежнюю позицию
    last_column = list(transformed)
    last_column.insert(sentinel_position, 256)

    n = len(last_column)

    # Первый столбец получается сортировкой последнего столбца
    first_column = sorted(last_column)

    # Определяем первое вхождение каждого символа
    first_occurrence = {}

    for i, char in enumerate(first_column):
        if char not in first_occurrence:
            first_occurrence[char] = i

    # Строим переходы между строками по одинаковым символам
    occurrences = {}
    next_row = [0] * n

    for i, char in enumerate(last_column):
        rank = occurrences.get(char, 0)

        next_row[i] = first_occurrence[char] + rank
        occurrences[char] = rank + 1

    # Восстанавливаем исходные данные
    result = [0] * n
    row = primary_index

    for i in range(n - 1, -1, -1):
        result[i] = last_column[row]
        row = next_row[row]

    # Убираем специальный символ конца
    result = [char for char in result if char != 256]

    return bytes(result)


# 3. Узел дерева Хаффмана
class Node:
    counter = 0

    def __init__(self, char=None, freq=0, left=None, right=None):
        self.char = char # Символ
        self.freq = freq # Частота символа
        self.left = left # Левый узел
        self.right = right # Правый узел

        self.order = Node.counter # Порядок узлов
        Node.counter += 1

    def __lt__(self, other): # Сравнивание узлов (частоты, порядок)
        if self.freq != other.freq:
            return self.freq < other.freq

        return self.order < other.order


# 4. Построение дерева
def build_tree(data):

    frequencies = Counter(data) # Подсчёт частат

    heap = [] # Массив очереди

    for char in sorted(frequencies): # Создание отдельного узла для каждого байта
        freq = frequencies[char]
        heapq.heappush(heap, Node(char, freq))

    if len(heap) == 1:
        only_node = heapq.heappop(heap)
        return Node(
            freq=only_node.freq,
            left=only_node
        )

    while len(heap) > 1:
        # Строиться дерево общей частотой
        left = heapq.heappop(heap) # Извлекает два узла с наименьшими частотами
        right = heapq.heappop(heap) # Объединяет их в новый узел с суммарной частотой и возвращает его в очередь

        parent = Node(
            freq=left.freq + right.freq,
            left=left,
            right=right
        )

        heapq.heappush(heap, parent)

    return heap[0]


# 5. Создание кодов Хаффмана
# После создания дерева, прорграмма проходит по нему и создаёт каждому символу код. Лево - 0. Право - 1
def build_codes(node, code="", codes=None):

    if codes is None:
        codes = {}

    if node.char is not None:
        codes[node.char] = code if code else "0"
        return codes

    build_codes(node.left, code + "0", codes)
    build_codes(node.right, code + "1", codes)

    return codes


# 6. Сжатие данных
# Превращает исходные данные в последовательность битов
def compress_data(data):

    if not data:  # Подсчёт частот элементов (как часто они встречаются)
        return b"", [0] * 256, 0

    frequencies = [0] * 256

    for byte in data:
        frequencies[byte] += 1

    tree = build_tree(data)
    codes = build_codes(tree)

    bits = "" # Замена байтов их кодами

    for byte in data:
        bits += codes[byte]

    bit_length = len(bits)

    compressed = bytearray()

    # Один байт содержит 8 бит. Поэтому программа делит строку на группы по 8 символов
    for i in range(0, len(bits), 8): # Строка из нулей и едениц

        byte_bits = bits[i:i + 8]

        if len(byte_bits) < 8:
            byte_bits += "0" * (8 - len(byte_bits)) # Если последняя группа короче восьми бит, она дополняется нулями

        compressed.append(int(byte_bits, 2)) # Превращение двоичной строки в число

    return bytes(compressed), frequencies, bit_length # Возвращение трёх значений: сжатые данные, частота, кол-во бидов до доп. нулями


# 7. Распаковка данных (обратная операция)
# Строит дерево и считает сжатые данные побитно.
# При нахождении узла с символом, символ добавляется в результат
def decompress_data(compressed, frequencies, bit_length, original_size):

    if original_size == 0: # Если размер исходных данных равен нулю, возвращаем пустую строку
        return b""

    heap = []  # Очередь для построения дерева Хаффмана

    # Создание узлов для каждого символа с ненулевой частотой
    for byte, freq in enumerate(frequencies):
        if freq > 0:
            heapq.heappush(heap, Node(byte, freq))

    # Если в очереди только один узел, возвращаем его как дерево
    if len(heap) == 1:
        node = heap[0] # Единственный узел в дереве
        return bytes([node.char]) * original_size # Возвращаем исходные данные

    while len(heap) > 1: # Построение дерева Хаффмана до тех пор, пока в очереди не останется один узел

        left = heapq.heappop(heap)  # Извлечение узлов с наименьшей частотой
        right = heapq.heappop(heap)  # Извлечение следующего узла с наименьшей частотой

        parent = Node(  # Создание нового родительского узла
            freq=left.freq + right.freq,
            left=left,
            right=right
        )

        heapq.heappush(heap, parent)  # Добавление родительского узла обратно в очередь

    tree = heap[0]  # Корень дерева Хаффмана
    current = tree  # Текущий узел при декодировании
    result = bytearray()  # Буфер для хранения распакованных данных

    bits_read = 0  # Счётчик прочитанных битов

    for byte in compressed:  # Проходим по каждому байту сжатых данных

        for bit_position in range(7, -1, -1):  # Проходим по каждому биту в байте

            if bits_read >= bit_length:  # Если прочитано достаточно битов, выходим из цикла
                break

            bit = (byte >> bit_position) & 1  # Извлечение текущего бита

            if bit == 0:  # Переход в левое поддерево при бите 0
                current = current.left
            else:  # Переход в правое поддерево при бите 1
                current = current.right

            if current.char is not None:  # Если достигнут листовой узел с символом
                result.append(current.char)  # Добавляем символ в результат
                current = tree  # Возвращаемся к корню дерева для следующего символа

            bits_read += 1  # Увеличиваем счётчик прочитанных битов

    return bytes(result)  # Возвращаем распакованные данные в виде байтового объекта


# 8. Упаковка файла
def compress_file(source_file, archive_file):

    with open(source_file, "rb") as file: # Чтение в двоичном режиме
        data = file.read()

    # Сначала применяем BWT к исходным данным
    transformed, sentinel_position, primary_index = bwt_transform(data)

    print("\nBWT успешно выполнено.")
    print(f"Размер исходных данных: {len(data):,} байт")
    print(f"Размер после BWT: {len(transformed):,} байт")
    print(f"Позиция символа конца: {sentinel_position}")
    print(f"Индекс исходной строки: {primary_index}")

    # После BWT сжимаем преобразованные данные методом Хаффмана
    compressed, frequencies, bit_length = compress_data(transformed)

    header = b"HUF2" # Формат архива с поддержкой BWT
    header += struct.pack(">Q", len(data)) # Размер исходного файла
    header += struct.pack(">Q", sentinel_position) # Позиция символа конца BWT
    header += struct.pack(">Q", primary_index) # Индекс исходной строки BWT
    header += struct.pack(">256I", *frequencies) # Частота всех байтов. Дерево при распоковке
    header += struct.pack(">Q", bit_length) # Количество битов

    with open(archive_file, "wb") as file: # Запись в двоичном формате
        file.write(header)
        file.write(compressed)

    return len(data), os.path.getsize(archive_file)


# 9. Распаковка файла
def decompress_file(archive_file, output_file):

    with open(archive_file, "rb") as file:
        magic = file.read(4)

        if magic != b"HUF2":
            raise ValueError("Неверный формат архива.")

        original_size = struct.unpack(">Q", file.read(8))[0]
        sentinel_position = struct.unpack(">Q", file.read(8))[0]
        primary_index = struct.unpack(">Q", file.read(8))[0]

        frequencies = list(
            struct.unpack(">256I", file.read(1024))
        )
        bit_length = struct.unpack(">Q", file.read(8))[0]

        compressed = file.read()

    # Сначала восстанавливаем данные после сжатия Хаффмана
    transformed = decompress_data(
        compressed,
        frequencies,
        bit_length,
        original_size
    )

    # Затем выполняем обратное преобразование BWT
    data = inverse_bwt(
        transformed,
        sentinel_position,
        primary_index
    )

    with open(output_file, "wb") as file:
        file.write(data)


# 10. Расчёт степени сжатия SSR
def calculate_ssr(source_size, compressed_size):

    if source_size == 0:
        return 0

    return (1 - compressed_size / source_size) * 100


# 11. Сравнение через diff
def compare_files(source_file, unpacked_file):

    result = subprocess.run(
        ["diff", "-q", source_file, unpacked_file],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


# 12. Главная функция
def main():

    source_file = "book.txt"
    archive_file = "book.huff"
    unpacked_file = "book_unpacked.txt"

    if not os.path.exists(source_file):
        print(f"Файл не найден: {source_file}")
        print("Поместите исходную книгу в папку программы.")
        return

    # Medium: упаковка файла

    source_size, compressed_size = compress_file(
        source_file,
        archive_file
    )

    print("\nФайл успешно сжат.")

    print(f"Размер исходного файла: {source_size:,} байт")
    print(f"Размер архива: {compressed_size:,} байт")

    # Rare: степень сжатия SSR в процентах
    ssr = calculate_ssr(
        source_size,
        compressed_size
    )

    print(f"Степень сжатия SSR: {ssr:.2f}%")

    if ssr > 0:
        print("SSR положительная.")
    else:
        print("SSR не положительная.")

    # Medium: распаковка файла
    decompress_file(
        archive_file,
        unpacked_file
    )

    print("\nФайл успешно распакован.")

    # Rare: сравнение через diff
    if compare_files(source_file, unpacked_file):
        print("diff: файлы полностью совпадают.")
    else:
        print("diff: файлы отличаются.")


if __name__ == "__main__":
    main()

    # АААААИИИВ
    # 1 01 00
    # 5 3 1 - частота. Объединяет наименьшие узлы и 3 + 1 = 4. 4 + 5 = 9 (равно количеству символов).
    # Замена каждого символа его кодом - 1 1 1 1 1 01 01 01 00 = 1111101010100 - 13 бит вместо 9 байтов.
    # Программа разбивает строку по 8 бит и добавляет нулями если нужно - 11111010 10100000

    # Обратное преобразование
    # Программа строит такое же дерево и проходит по нему бит за битом

    # BWT — Оно переставляет символы текста так, чтобы одинаковые символы чаще оказывались рядом.
    # BWT добавляет специальный символ конца $, а затем строит все циклические сдвиги строки
    # АААААИИИВ$
	# ААААИИИВ$А
	# АААИИИВ$АА
    # Теперь сортируем полученные строки по алфавиту. После сортировки берём последний символ каждой строки - ВАААААИИИ$