# Ares INI

> 模块名：`formats.ini`  
> 此模块全部 API 均可直接从`pyalert2yr`包中取用。

```python
>>> import pyalert2yr.formats.ini as ini
>>> ini.__all__
['INIClass', 'INISection', 'iniTreeDFSWalk']
```

## 前言
其实 Python 有个读写 INI 的标准库`configparser`，但读起红红的 INI 就显得比较鸡肋：
- 弹头的`Verses`值是对多个护甲的伤害修正比（`100%,10%,10%, ...`），读取可能引发`InterpolationError`。

> 实际应为 Versus。西木头当年拼错了。

- 显然标准 INI 库不支持 Ares 新引入的 INI [扩展语法](https://github.com/ClLab-YR/Chloride.RA2Scripts/blob/master/IniExt.ReadMe.md)：
    - 继承：`[Child]:[Parent]`（`Parent`必须在`Child`之前，并且不支持多继承）
    - 丢弃追加：`+= NewItem`（允许多个`+=`同时出现在一个小节中）
    - INI 嵌套：`[#include]`

虽然 C# 那边[岛风@frg2089](https://github.com/frg2089)也写过库，但我毕竟事脚本壬，而 Python 源代码正好可以方便地嵌入存储库，当做脚本运行。  

综上所述，我还是自行写了这么一版 Python 实现。

## INI 小节
与标准库不同，`INISection`更倾向于 Dict 那样的设计。它不记录小节名，也不记录继承关系，纯纯的是个键值对字典。  
但 INI 与标准 Dict 有一点不同：它有注释。为了避免注释内容丢失导致 Git 库里出现大段 Diff，`INISection`也设法实现了对注释的存储（但**不会对注释做任何修改**）。

- `summary`字段：简介，即小节声明的尾随注释（比如`[A]  ;desc`的`; desc`）

```python
class INISection(MutableMapping):
    """ INI 小节的字典*原则上*允许以下键值对记录：
    - key: [value],
    - key2: [value, trail_comment],
    - f";{comment_guid}": [None, line_comment]
    还请注意，实际运行中并不会对数据类型做额外的验证。
    此外，简便起见，键值对的存取均忽略注释。"""
    def __init__(self, **pairs_to_import):
        """初始化 INI 键值对字典。可以通过关键字参数从别处导入数据。"""
    def __setitem__(self, k: str, v: str):
        """实现 self[k] 存键值操作。
        值得注意的是，若 k == '+'，则实际存入的键名会被替换为 +%d。
        整数 %d 会从 0 开始逐渐累加。"""

    # - 取、删除键值和计数操作不再详细列出。
    # - 对键值对的序列捕获（keys values items）和迭代操作（__iter__）
    #   均忽略纯注释行 line_comment 和尾随注释 comment。
```

## INI 文档
`INIClass`维护整个 INI 文档（甚至一棵 INI 树），但**不负责对 ini 文件的读写**。

- `inheritance`字段：继承关系字典，记录整个文档（树）的小节继承。  
  以[前言](#前言)为例，键为子代`Child`，值为亲代`Parent`。
- `header`字段：文档头部“小节”，记录文件最开头的注释，以及游离在任何小节之外的键值对。

> 标准库不允许键值对在任何小节声明`[xx]`之前，否则读取时会引发`MissingSectionHeaderError`异常。

```python
class INIClass(MutableMapping):
    def __init__(self):
        """初始化空 INI 字典。"""

    # 用小节名作为键的存、取、删、迭代、计数操作均不再赘述。
    # 唯一需要补充的是，删除小节时会*连带删除它的继承关系*。

    def getTypeList(self, section):
        """获取某一小节的*有序、不重复*值表（通常用在“注册表”上）。"""
        # “注册表”这东西，你不妨理解为类的抽象。
        # INI 里记录的大抵就是这些“子类”的信息。
        # 比如：[InfantryTypes] -> 0=ChlorideP -> 游戏里两个同种步兵 a, b
        # 类比：Animal          -> Cat         -> 两只猫猫 toutou, beibei
    def recursiveFind(self, section, key) -> Sequence[Optional[str]]:
        """从某一子代小节开始，向亲代逐级查找某键。
        - 若找到：返回（该键所在小节名，该键的值）二元组；
        - 若没找到：返回 (None, None) 二元组。"""
    def rename(self, old, new):
        """重命名某小节。若没找到旧小节，或新小节已经存在，则返回 False。"""
    def update(self, section: str, entries: INISection, 
               inherit: Optional[str] = None):
        """根据给定的小节信息更新文档。就像 dict 一样（无则增，有覆盖）。"""
```

## INI 读写
单独写这么一个类的原因是：标准库也好，我旧版的实现也好，读写起来不够“一气呵成”：
```python
a = INIClass()
a.read(...)
```
此外，长期以来我的 INI 读写都是同步的，姑且是打算重写一版提高并发度吧。

```python
class INIParser:
    """用以读取某一棵 INI *树*，或是将 INI 字典写回某个 INI *文件*。"""
    def __init__(self):
        """无参。** 读 方法必须实例化该类方可调用**。"""
    def dfsWalk(self, rootini_path) -> INIClass:
        """ *试图*用深度优先方式读取 INI 树（这也是 Ares 的读法）。

        说“试图”是因为，遍历遵循的下面两条假设可能无法成立：
        1. 所有 INI 均有共同的父目录：
            - D:/yr_Ares/
                - rulesmd.ini       [root]
                - Includes/
                    - rules_GDI.ini [sub: sub dir of root]
                - rules_hotfix.ini  [sub: same dir with root]
        2. 所有 INI 均可读（未被加密，未被打包进 MIX）。
        一旦某 INI 无法找到，或者不可读，该方法就会弹出警告，并跳过不读该文件。"""
    def read(self, ini_path) -> INIClass:
        """读取单个 INI 文件。"""
        # 读方法不需要指定编码的原因是：
        # 我是以'rb'方式打开的，读到的字节流会逐段解码。
    @staticmethod
    def write(
        doc: INIClass, ini_path, encoding='utf-8', *,
        pairing='=', blankline=1):
        """另存为一个 INI 文件。

        关键字 pairing 控制键值之间如何连接，默认"key=value"这样；
        关键字 blankline 控制两个小节之间空多少行，默认 1 行。"""
```

