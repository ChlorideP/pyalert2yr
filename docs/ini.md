# Ares INI

> 模块名：`ini`
> 此模块全部 API 均可直接从包中取用。

~~算是 PyMapRA2 的遗产。可惜旧文档已经找不到了，我也懒得重新写一份。~~

```python
>>> import pyalert2yr.ini as ini
>>> ini.__all__
['INIClass', 'INISection', 'scanINITree']
>>>
```

## 查找子 ini 树
```python
def scanINITree(ini_root_path) -> list:
    """搜索 [#includes] 子 INI，并【尽可能】按游戏读取的顺序排列。"""
```

> `ini_root_path` 根 INI 文件路径  
Windows 的路径用`\`分隔，传参时不妨`r"D:\YR\RULESMD.INI"`。

> “尽可能”是指，我们无法处理违反下列假设的子 INI 条目（比如置于 MIX 或加密）。
> - 所有子 INI 均与根 INI 处于同一目录，或是其子目录：
> ```
> [root] D:\YR\rulesmd.ini
> [sub] D:\YR\rules_hotfix.ini
> [sub] D:\YR\subs\rules\globals.ini
> ```
> - 所有子 INI 均可读。

## INI 小节

与`dict[str, str]`类似，但实现了类型转换。  
对小节的键值**写**操作时，会自动将键值转为`str`类型；读操作如需强转则需要调用`get()`。

```python
class INISection(MutableMapping):
    def __init__(self, section_name: str, parent=None, **kwargs):
    def find(self, key):
        """递归查找，直至找不到双亲为止。"""
    def get(self, key, converter: Callable[[str], object], default=None):
        """获取 ini 值，并强转为对应类型。若找不到，返回 default.

        注 - 部分类型转换与 Python 原生实现不同：
        转为`bool`类型时，会检查值的首字符。1 t y 即为 True，0 f n 为 False。
        转为`list`时，会以 , 为分隔，拆成一个数组。
        """
    def sortPairs(self, key=None, *, reverse=False):
        """与 sorted() 类似，（默认按键名升序）排列键值对。"""
```

## INI 文档

实际上并未显式继承`MutableMapping`，但仍实现了部分字典操作。

```python
class INIClass:
    def __init__(self):
    def __setitem__(self, k, v: INISection | MutableMapping):
    def getTypeList(self, section_name):
        """返回去重的注册表数组。"""
    def clear(self):
        """清空整个 INI 文档。"""
    def rename(self, old, new):
        """重命名小节。若 old 不在文档中，或是已经有 new，则操作失败。"""
    # 带有 Stream 的读写操作需要结合 with 食用。
    def writeStream(self, fp: TextIOWrapper, pairing='=', blankline=1):
        """向打开的写文件流输出 ini 文本。
        pairing 决定键和值之间如何连接。默认 key=val。
        blankline 则决定两个小节之间空几行。
        """
    def readStream(self, stream: TextIOWrapper):
        """读取单个打开的文件流。"""
    def read(self, *inis, encoding=None):
        """批量读入 ini（可以通过 scanIncludes() 获取）。
        编码由 chardet 库自动判别。"""
```