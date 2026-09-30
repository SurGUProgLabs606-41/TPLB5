import os
import heapq
import struct
import subprocess
from collections import Counter


# 1. Узел дерева Хаффмана

class Node:
    counter = 0

    def __init__(self, char=None, freq=0, left=None, right=None):
        self.char = char
        self.freq = freq
        self.left = left
        self.right = right

        self.order = Node.counter
        Node.counter += 1

    def __lt__(self, other):
        if self.freq != other.freq:
            return self.freq < other.freq

        return self.order < other.order


# 2. Построение дерева

def build_tree(data):

    frequencies = Counter(data)

    heap = []

    for char, freq in frequencies.items():
        heapq.heappush(heap, Node(char, freq))

    if len(heap) == 1:
        only_node = heapq.heappop(heap)
        return Node(
            freq=only_node.freq,
            left=only_node
        )

    while len(heap) > 1:

        left = heapq.heappop(heap)
        right = heapq.heappop(heap)

        parent = Node(
            freq=left.freq + right.freq,
            left=left,
            right=right
        )

        heapq.heappush(heap, parent)

    return heap[0]


# 3. Создание кодов Хаффмана

def build_codes(node, code="", codes=None):

    if codes is None:
        codes = {}

    if node.char is not None:
        codes[node.char] = code if code else "0"
        return codes

    build_codes(node.left, code + "0", codes)
    build_codes(node.right, code + "1", codes)

    return codes


# 4. Сжатие данных

def compress_data(data):

    if not data:
        return b"", [0] * 256, 0

    frequencies = [0] * 256

    for byte in data:
        frequencies[byte] += 1

    tree = build_tree(data)
    codes = build_codes(tree)

    bits = ""

    for byte in data:
        bits += codes[byte]

    bit_length = len(bits)

    compressed = bytearray()

    for i in range(0, len(bits), 8):

        byte_bits = bits[i:i + 8]

        if len(byte_bits) < 8:
            byte_bits += "0" * (8 - len(byte_bits))

        compressed.append(int(byte_bits, 2))

    return bytes(compressed), frequencies, bit_length


# 5. Распаковка данных

def decompress_data(compressed, frequencies, bit_length, original_size):

    if original_size == 0:
        return b""

    heap = []

    for byte, freq in enumerate(frequencies):
        if freq > 0:
            heapq.heappush(heap, Node(byte, freq))

    if len(heap) == 1:
        node = heap[0]
        return bytes([node.char]) * original_size

    while len(heap) > 1:

        left = heapq.heappop(heap)
        right = heapq.heappop(heap)

        parent = Node(
            freq=left.freq + right.freq,
            left=left,
            right=right
        )

        heapq.heappush(heap, parent)

    tree = heap[0]
    current = tree
    result = bytearray()

    bits_read = 0

    for byte in compressed:

        for bit_position in range(7, -1, -1):

            if bits_read >= bit_length:
                break

            bit = (byte >> bit_position) & 1

            if bit == 0:
                current = current.left
            else:
                current = current.right

            if current.char is not None:
                result.append(current.char)
                current = tree

            bits_read += 1

    return bytes(result)


# 6. Упаковка файла

def compress_file(source_file, archive_file):

    with open(source_file, "rb") as file:
        data = file.read()

    compressed, frequencies, bit_length = compress_data(data)

    header = b"HUF1"
    header += struct.pack(">Q", len(data))
    header += struct.pack(">256I", *frequencies)
    header += struct.pack(">Q", bit_length)

    with open(archive_file, "wb") as file:
        file.write(header)
        file.write(compressed)

    return len(data), os.path.getsize(archive_file)


# 7. Распаковка файла

def decompress_file(archive_file, output_file):

    with open(archive_file, "rb") as file:
        magic = file.read(4)

        if magic != b"HUF1":
            raise ValueError("Неверный формат архива.")

        original_size = struct.unpack(">Q", file.read(8))[0]
        frequencies = list(
            struct.unpack(">256I", file.read(1024))
        )
        bit_length = struct.unpack(">Q", file.read(8))[0]

        compressed = file.read()

    data = decompress_data(
        compressed,
        frequencies,
        bit_length,
        original_size
    )

    with open(output_file, "wb") as file:
        file.write(data)


# 8. Расчёт степени сжатия

def calculate_ssr(source_size, compressed_size):

    if source_size == 0:
        return 0

    return (1 - compressed_size / source_size) * 100


# 9. Сравнение через diff

def compare_files(source_file, unpacked_file):

    result = subprocess.run(
        ["diff", "-q", source_file, unpacked_file],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


# 10. Главная функция

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

    # Rare: степень сжатия SSR

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