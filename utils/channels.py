from dataclasses import dataclass

from config import CHANNELS_IDS


@dataclass(frozen=True)
class Channel:
    callback: str
    name: str
    chat_id: int


CHANNELS = [
    Channel(callback='text', name='«Текстовой»', chat_id=CHANNELS_IDS[0]),
    Channel(callback='draw', name='«Рисовательный»', chat_id=CHANNELS_IDS[1]),
]

CHANNELS_BY_CALLBACK = {ch.callback: ch for ch in CHANNELS}
CHANNELS_BY_CHAT = {ch.chat_id: ch for ch in CHANNELS}


def find_channel_name(channel_id: int):
    return CHANNELS_BY_CHAT[channel_id].name


def find_by_callback(callback: str):
    return CHANNELS_BY_CALLBACK[callback]
