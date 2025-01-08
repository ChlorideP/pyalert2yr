# -*- encoding: utf-8 -*-
# @File   : rw.py
# @Time   : 2024/10/10 01:04:45
# @Author : Kariko Lin

"""Note: This package has **no plan on MIX implement**
thus the INI parser may not get a real case INI tree.

We do parsing based on the following consumption:
1. These INIs are placed together, in other words, IN A SAME FOLDER.
Like this case:

    - c&c2yuri  (where `gamemd.exe` exists)
        - rulesmd.ini
        - rules_global.ini
        - INIs
            - rules_GDI.ini
            - rules_Nod.ini

    This is also what [INIValidator]\
(https://github.com/Super-StarX/INIValidator) does.

2. These INIs are ALL READABLE, without any compression or encryption.
"""

from io import StringIO, TextIOBase
from os import PathLike
from os.path import split, join, exists
from multiprocessing.pool import Pool, ThreadPool
from warnings import warn

import chardet

from .model import IniClass, IniSectionMeta
from ..abstract import FileHandler


class IniParser(FileHandler[IniClass]):
    def __init__(self, rootfile: str, encoding: str | None = None):
        super().__init__(rootfile)
        self._codec = encoding

    @staticmethod
    def readstream(buf: TextIOBase, ins: IniClass | None = None) -> IniClass:
        """读取解码好的字符串流。

        如没有特殊需求，直接调用`self.read()`便是。
        """
        if ins is None:
            ins = IniClass()
        this_sect = ins.header
        while i := buf.readline():
            if i[0] == '[':
                section = dict(zip(
                    ['decl', 'base'],
                    [j.strip()[1:-1] for j in i[:i.find(';')].split(':')])
                )
                this_sect = ins.setdefault(section['decl'], {})
                # always update inheritance
                if 'base' in section:
                    ins.inherits[section['decl']] = [section['base']]
            elif '=' in i:
                key, val = i.split('=', 1)
                key = key.strip()
                if ';' not in key:
                    this_sect[key] = val.split(';')[0].strip()
                    if key == '$Inherits':
                        # override with Phobos inherit
                        # since Phobos overrides Ares one.
                        ins.inherits[section['decl']] = [
                            j.strip() for j in this_sect[key].split(',')
                        ]
        return ins

    @staticmethod
    def _decode_file(filename: str) -> StringIO:
        with open(filename, 'rb') as fp:
            raw = fp.read()

        codec = chardet.detect(raw)
        if codec is None or codec['confidence'] < 0.8:
            codec = {'encoding': 'utf-8'}

        # fallbacks
        try:
            buf = raw.decode(codec['encoding'])
        except UnicodeDecodeError:
            buf = raw.decode('gbk')
        return StringIO(buf)

    def read(self) -> IniClass:
        """读取`IniParser`实例指定的文件。

        注：欲处理`[#include]`拆分 INI 树，请改用`IniTreeParser`。
        """
        try:
            # when encoding is None, `open()` would fallback to system default.
            # and when encoding got wrong,
            # just `UnicodeDecodeError` and fallback to `chardet`.
            with open(self._fn, 'r', encoding=self._codec) as fp:
                return self.readstream(fp)
        except UnicodeDecodeError:
            return self.readstream(self._decode_file(self._fn))

    def __output_section(
        self, meta: IniSectionMeta,
        use_phobos: bool = False, delimiter: str = '='
    ) -> str:
        ret = f'[{meta["section"]}]'
        if meta['parents'] is not None:
            if use_phobos:
                meta['pairs']['$Inherits'] = ','.join(meta["parents"])
            elif len(meta['parents']) > 2:
                warn(
                    '你并未选择按 Phobos 方式保存，'
                    f'但 {ret} 中不止一个父小节：{meta['parents']}。')
            else:
                ret += f':[{meta["parents"][0]}]'
        for k, v in meta['pairs'].items():
            ret += f'\n{k}{delimiter}{v}'
        return ret

    def write(
        self, instance: IniClass, *,
        use_phobos: bool = False,
        blank_lines: int = 1,
        delimiter: str = '='
    ) -> None:
        """保存到*一个* INI 文件。

        注：
        1. 此操作*不会复原*合并过的拆分 INI 树。
        2. 若未设`use_phobos=True`，且继承了两个及以上父小节，
        则予以告警，*且不保留任何继承关系*。
        """
        # may be able to use some async/multiprocessing/threading stuffs.
        pool = Pool()
        buffers = pool.map(
            lambda x: self.__output_section(
                instance._get_meta(x), use_phobos, delimiter),
            instance.keys()
        )
        pool.close()
        pool.join()
        with open(self._fn, 'w', encoding=self._codec) as fp:
            for i in buffers:
                fp.write(i)
                fp.write('\n' * blank_lines)

    def __str__(self) -> str:
        return "INI tree root: " + super().__str__() + f"({self._codec})"


class IniTreeParser(IniParser):
    def __init__(self, rootfile: str, encoding: str | None = None) -> None:
        super().__init__(rootfile, encoding)
        self._root = split(rootfile)[0]

    def readfiles(
        self,
        instance: IniClass | None = None,
        *splited_stub: str
    ) -> IniClass:
        """除读取`IniTreeParser`实例指定的文件之外，
        还依次读取`splited_stub`里的拆分 INI（不一定是因为`[#include]`）。

        注：拆分 INI 需要传入*绝对路径*。本方法并不会假定这些分片的位置。
        """
        # 同步读，最简单的一集
        # 主要 Python 的异步 IO 全是基于网络的 (aiohttps, ...)，文件的基础设施不得行
        # 当然我是可以考虑线程池之类的，但……可能比同步还慢。
        if instance is None:
            instance = super().read()
        for i in splited_stub:
            self.readstream(self._decode_file(join(self._root, i)), instance)
        return instance

    def read(self, *, bfs: bool = False) -> IniClass:
        """读取`IniParser`实例指定的文件。

        默认情况下会根据`[#include]`记录的相对路径，深度优先搜索拆分 INI。
        （所以本模块假设所有 INI 均位于同一个文件夹之下）

        另有 modder 发现拆分 INI 是按层级顺序依次读取（或者说，广度优先搜索）。
        由于与 Ares 官方文档和 Phobos 文档介绍的读取顺序相左，本方法默认不启用这种搜索模式，
        你可以指定`bfs=True`自行切换。
        """
        ret = super().read()
        if '#include' not in ret:
            return ret
        stack, root = list(ret['#include'].values()), [self._root]
        stack.reverse()
        while stack:
            i = join(root[-1], stack.pop())
            root.append(split(i)[0])
            if not exists(i):
                warn(f'在读取`{self._fn}`时，未找到`{i}`。')
                root.pop()
                continue
            ret['#include'].clear()
            ret = self.readfiles(ret, i)
            _ = list(ret['#include'].values())
            _.reverse()
            if bfs:
                stack = _ + stack
            else:
                stack.extend(_)
            root.pop()
        return ret
