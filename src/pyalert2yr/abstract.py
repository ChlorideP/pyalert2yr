# -*- encoding: utf-8 -*-
# @File   : abc.py
# @Time   : 2024/09/08 20:22:30
# @Author : Kariko Lin

from abc import ABCMeta, abstractmethod
from typing import TypeVar

T = TypeVar('T')


class SerializedComponents[T](metaclass=ABCMeta):
    @abstractmethod
    def reset_seek(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def seekable(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def next(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def current(self) -> T:
        raise NotImplementedError

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


class FileHandler[T](metaclass=ABCMeta):
    def __init__(self, filename: str) -> None:
        self._fn = filename

    @abstractmethod
    def read(self) -> T:
        raise NotImplementedError

    @abstractmethod
    def write(self, instance: T) -> None:
        raise NotImplementedError

    def __str__(self) -> str:
        return self._fn
