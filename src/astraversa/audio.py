# pylint: disable=no-name-in-module,invalid-name,unused-import
from typing import Any, TypeVar, Generic
from abc import ABC, abstractmethod
from pyray import (
    load_sound,
    unload_sound,
    set_sound_volume,
    Sound,
    load_music_stream,
    unload_music_stream,
    set_music_volume,
    Music,
    play_music_stream,
    stop_music_stream,
    play_sound,
    stop_sound,
    update_music_stream,
    update_sound,
    is_music_stream_playing,
)

DataType = TypeVar("DataType")


class AudioHandler(ABC, Generic[DataType]):
    """Base Audio handler"""

    def __init__(self, path: str, volume: float = 0) -> None:
        self._path = path
        self._volume = volume
        self._data: DataType | None = None

    @abstractmethod
    def load(self):
        """Load Audio stream"""

    @abstractmethod
    def unload(self):
        """Unload Audio stream"""

    @abstractmethod
    def play(self):
        """Play Audio stream"""

    @abstractmethod
    def stop(self):
        """Stop Audio stream"""

    @abstractmethod
    def update(self):
        """Update Audio stream"""

    @property
    def is_playing(self):
        """Is this stream playing?"""
        raise NotImplementedError

    @property
    def volume(self):
        """Volume"""
        return self._volume

    @volume.setter
    def volume(self, val: float):
        if val < 0 or val > 1:
            raise ValueError("Volume must be between 1 and 0")
        self._volume = val

    @property
    def path(self):
        """Path"""
        return self._path

    @property
    def data(self) -> DataType:
        """Data stream"""
        if not self._data:
            raise ValueError("Not initialized")
        return self._data

    @property
    def loaded(self):
        """is stream loaded?"""
        return self._data is not None

HandlerType = TypeVar("HandlerType", bound=AudioHandler[Any])


class SoundHandler(AudioHandler[Sound]):
    """Sound handler"""

    def __init__(self, path: str, volume: float = 0) -> None:
        super().__init__(path, volume)
        self._data: Sound | None = None

    @property
    def is_playing(self):
        """Is this sound playing?"""
        return False

    def load(self):
        """Load sound"""
        self._data = load_sound(self._path)
        set_sound_volume(self.data, self.volume)

    def unload(self):
        """Unload sound"""
        unload_sound(self.data)
        self._data = None

    def play(self):
        """Play sound"""
        play_sound(self.data)

    def update(self):
        """This function is no-op"""

    def stop(self):
        """Stop sound"""
        stop_sound(self.data)


class MusicHandler(AudioHandler[Music]):
    """Music Handler"""

    def __init__(self, path: str, volume: float = 0) -> None:
        super().__init__(path, volume)
        self._data: Music | None = None

    @property
    def is_playing(self):
        """Is this music playing?"""
        return is_music_stream_playing(self.data)

    def load(self):
        """Load music"""
        self._data = load_music_stream(self._path)
        set_music_volume(self.data, self.volume)

    def unload(self):
        """Unload music"""
        unload_music_stream(self.data)
        self._data = None

    def play(self):
        """Play music"""
        play_music_stream(self.data)

    def update(self):
        """Update music"""
        update_music_stream(self.data)

    def stop(self):
        """Stop music"""
        stop_music_stream(self.data)


class AudioManager:
    """Audio Manager"""

    def __init__(
        self, initializers: dict[str, HandlerType] | None = None, volume: float = 1.0
    ):
        self._audio: dict[str, AudioHandler[Any]] = {}
        self._initializers = initializers
        self._volume = volume

    def register(self, key: str, handler: HandlerType):  # type: ignore
        """Register an audio"""
        self._audio[key] = handler
        handler.load()

    def load(self):
        """Load audio instances"""
        if self._initializers:
            for key, value in self._initializers.items():
                value.volume = self._volume
                value.load()
                self._audio[key] = value

    def unload(self):
        """Unload all stream"""
        for audio in self._audio.values():
            audio.unload()

    def update(self):
        """Update all stream"""
        for audio in self._audio.values():
            if not isinstance(audio, MusicHandler):
                continue
            if audio.loaded:
                audio.update()

    def remove(self, key: str):
        """Remove an audio"""
        del self._audio[key]

    def get(self, name: str, expected_type: type[HandlerType]) -> HandlerType:
        """Get a stream"""
        data = self._audio[name]
        if not isinstance(data, expected_type):
            raise TypeError(
                f"{repr(data)} is not an object of {expected_type.__name__}"
            )
        return data
