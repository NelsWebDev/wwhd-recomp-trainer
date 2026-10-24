import unittest

from trainer import GameMemory, OFFSETS, pack_value, unpack_value


class FakeMemory:
    def __init__(self):
        self.data = {}

    def read(self, address, size):
        return bytes(self.data.get(address + index, 0) for index in range(size))

    def write(self, address, data):
        for index, value in enumerate(data):
            self.data[address + index] = value


class TrainerMemoryTests(unittest.TestCase):
    def test_big_endian_scalar_round_trips(self):
        self.assertEqual(pack_value(0x1234, "u16"), b"\x12\x34")
        self.assertEqual(unpack_value(b"\x12\x34", "u16"), 0x1234)
        self.assertEqual(unpack_value(pack_value(1.25, "f32"), "f32"), 1.25)

    def test_invalid_scalar_is_rejected(self):
        with self.assertRaises(ValueError):
            pack_value(256, "u8")
        with self.assertRaises(ValueError):
            unpack_value(b"\x00", "u16")

    def test_memory_uses_base_and_big_endian(self):
        backend = FakeMemory()
        game = GameMemory(backend, 0x10000000)
        game.write(OFFSETS["health"], 0x1234, "u16")
        self.assertEqual(backend.read(0x10000000 + OFFSETS["health"], 2), b"\x12\x34")
        self.assertEqual(game.read(OFFSETS["health"], "u16"), 0x1234)

    def test_range_read_uses_game_base(self):
        backend = FakeMemory()
        game = GameMemory(backend, 0x20000000)
        backend.write(0x20000000 + OFFSETS["map_grid"], bytes(range(49)))
        self.assertEqual(game.read_bytes(OFFSETS["map_grid"], 49), bytes(range(49)))

    def test_bit_updates_preserve_neighboring_flags(self):
        backend = FakeMemory()
        game = GameMemory(backend, 0)
        backend.write(OFFSETS["pearls"], b"\x80")
        game.set_bit(OFFSETS["pearls"], 1, True)
        self.assertEqual(game.read(OFFSETS["pearls"], "u8"), 0x82)
        game.set_bit(OFFSETS["pearls"], 7, False)
        self.assertEqual(game.read(OFFSETS["pearls"], "u8"), 0x02)


if __name__ == "__main__":
    unittest.main()
