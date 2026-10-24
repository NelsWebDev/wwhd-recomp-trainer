import unittest

from trainer import (
    GameMemory, OFFSETS, SAVE_POINTER, SAVE_PLAYER_DELTA, SaveNotLoaded,
    is_game_process, pack_value, unpack_value,
)

BASE = 0x10000000
SAVE_GUEST = 0x30000000


class FakeMemory:
    def __init__(self):
        self.data = {}

    def read(self, address, size):
        return bytes(self.data.get(address + index, 0) for index in range(size))

    def write(self, address, data):
        for index, value in enumerate(data):
            self.data[address + index] = value


def loaded_game():
    backend = FakeMemory()
    backend.write(BASE + SAVE_POINTER, (SAVE_GUEST - SAVE_PLAYER_DELTA).to_bytes(4, "big"))
    save = BASE + SAVE_GUEST
    backend.write(save, (40).to_bytes(2, "big"))
    backend.write(save + 2, (40).to_bytes(2, "big"))
    return backend, GameMemory(backend, BASE), save


class TrainerMemoryTests(unittest.TestCase):
    def test_big_endian_scalar_round_trips(self):
        self.assertEqual(pack_value(0x1234, "u16"), b"\x12\x34")
        self.assertEqual(unpack_value(b"\x12\x34", "u16"), 0x1234)
        self.assertEqual(unpack_value(pack_value(1.25, "f32"), "f32"), 1.25)
        self.assertEqual(unpack_value(pack_value(7, "u32"), "u32"), 7)

    def test_invalid_scalar_is_rejected(self):
        with self.assertRaises(ValueError):
            pack_value(256, "u8")
        with self.assertRaises(ValueError):
            unpack_value(b"\x00", "u16")

    def test_save_relative_address_follows_pointer(self):
        backend, game, save = loaded_game()
        game.write(OFFSETS["rupees"], 0x1234, "u16")
        self.assertEqual(backend.read(save + 4, 2), b"\x12\x34")
        self.assertEqual(game.read(OFFSETS["rupees"], "u16"), 0x1234)

    def test_static_address_uses_base_only(self):
        backend = FakeMemory()
        game = GameMemory(backend, BASE)
        game.write(OFFSETS["player_x"], 1.5, "f32")
        self.assertEqual(game.read(OFFSETS["player_x"], "f32"), 1.5)
        self.assertEqual(unpack_value(backend.read(BASE + 0x1046CD48, 4), "f32"), 1.5)

    def test_save_not_loaded(self):
        game = GameMemory(FakeMemory(), BASE)
        with self.assertRaises(SaveNotLoaded):
            game.read(OFFSETS["health"], "u16")

    def test_bit_updates_preserve_neighboring_flags(self):
        backend, game, save = loaded_game()
        game.write(OFFSETS["pearls"], 0x80, "u8")
        game.set_bit(OFFSETS["pearls"], 1, True)
        self.assertEqual(game.read(OFFSETS["pearls"], "u8"), 0x82)
        game.set_bit(OFFSETS["pearls"], 7, False)
        self.assertEqual(game.read(OFFSETS["pearls"], "u8"), 0x02)

    def test_process_name_matching(self):
        self.assertTrue(is_game_process("/Applications/Wind Waker HD.app/Contents/MacOS/Wind Waker HD"))
        self.assertTrue(is_game_process("/x/wwhd"))
        self.assertFalse(is_game_process("/Applications/Cemu.app/Contents/MacOS/Cemu"))


if __name__ == "__main__":
    unittest.main()
