# Ares INI

> 模块名：`formats.ini`  
> 此模块全部 API 均可直接从`pyalert2yr`包中取用。

```python
>>> import pyalert2yr.formats.ini as ini
>>> ini.__all__
['INIClass', 'INISection', 'INIParser']
```

## 前言
其实 Python 本有个读写 INI 的标准库`configparser`，但读起红红的 INI 就显得比较鸡肋：
- 弹头的`Verses`值是对多个护甲的伤害修正比`100%,10%,10%, ...`，读取可能引发`InterpolationError`。

> 实际应为 Versus。西木头当年拼错了。

- 显然标准 INI 库不支持 Ares 新引入的 INI [扩展语法](https://github.com/ClLab-YR/Chloride.RA2Scripts/blob/master/IniExt.ReadMe.md)：
    - 继承：`[Child]:[Parent]`（不支持多继承）
    - 丢弃追加：`+= NewItem`（允许多个`+=`同时出现在一个小节中）
    - INI 嵌套：`[#include]`

虽然 C# 那边[岛风@frg2089](https://github.com/frg2089)也写过库，但我毕竟事脚本壬，而 Python 源代码正好可以方便地嵌入存储库，当做脚本运行。  

综上所述，我还是自行写了这么一版 Python 实现。

## INI 小节
与标准库不同，`INISection`更倾向于 Dict 那样的设计。它不记录小节名，也不记录继承关系，纯纯的是个键值对字典。

```python
class INISection(MutableMapping):
    """ INI 小节的字典*原则上*允许 str: str 键值对，
    但实际运行中并不会对数据类型做额外的验证。"""
    def __init__(self, pairs_to_import: Mapping[str, str] = None):
        """初始化 INI 键值对字典。可以通过可选参数从别处导入数据。"""
    def __setitem__(self, k: str, v: str):
        """实现 self[k] 存键值操作。
        值得注意的是，若 k == '+'，则实际存入的键名会被替换为随机数。
        为避免碰撞，随机数取自 uuid1() 生成的第一段十六进制数。"""
        # 取、删除键值和计数操作不再详细列出。
    def toTypeList(self):
        """生成该小节的 *有序* *不重复* 值表。通常用于“注册表”。"""
```

> [!tip]
> 你可以将“注册表”理解为是一种“类的抽象”。  
> Python 也是一门面向对象的程序语言，我们就以 Python 为例：
> | |红警 2|Python 语言代码|
> |:--:| -- | -- |
> |父类|`[InfantryTypes]`|`class Animal:`|
> |子类|`114514 = TANY`，辅以同名小节`[TANY]`|`class Cat(Animal):`|
> |实例对象|游戏里通过复制中心训练的两个谭雅|`tou, bei = Cat(), Cat()`


## INI 文档
`INIClass`维护整个 INI 文档（甚至一棵 INI 树），但**不负责对 ini 文件的读写**。

- `inheritance`字段：继承关系字典，记录整个文档（树）的小节继承。  
  以[前言](#前言)为例，键为子代`Child`，值为亲代`Parent`。
- `header`字段：文档头部“小节”，记录文件最开头游离在任何小节之外的键值对。

> [!note]
> 标准库不允许键值对在任何小节声明`[xx]`之前，否则读取时会引发`MissingSectionHeaderError`异常。

```python
class INIClass(MutableMapping):
    def __init__(self):
        """初始化空 INI 字典。"""

    # 用小节名作为键的存、取、删、迭代、计数操作均不再赘述。
    # 唯一需要补充的是，删除小节时会*连带删除它的继承关系*。

    def add(self, section, entries: Mapping[str, str] = {},
            inherit: str = None):
        """新建小节，但与 Python 默认的 __setitem__ 不同：
        section 存在时，会将 entries 更新到已有的小节字典里，而不是覆盖。"""
    def findKey(self, section, key, recursive=False) -> Sequence[Optional[str]]:
        """查找某小节里的键值。若 recursive=True，且该小节找不到，则尝试向上逐级查找。
        - 若找到：返回（该键所在小节名，该键的值）二元组；
        - 若没找到：返回 (None, None) 二元组；
        - 若有继承但查找中断：返回（上一级小节名，None）二元组。"""
    def rename(self, old, new):
        """重命名某小节。若没找到旧小节，或新小节已经存在，则返回 False。"""
    def update(self, another: INIClass):
        """将另一个 INI 文档合并过来。
        此方法会复制继承关系、header 字段，并更新小节字典；
        但对于两边同时存在的小节，将更新 self[section]。"""
```

## INI 读写
单独写这么一个类的原因是：标准库也好，我旧版的实现也好，读写起来不够“一气呵成”：
```python
a = INIClass()
a.read(...)
```
此外，长期以来我的 INI 读写都是同步的，姑且是打算提高一下并发度吧。

> 当然实际上只在`readTree()`那里做了并发。对单个文件来说同步已足够快了。

### 读方法

> [!warning]
> 调用读方法前必须先实例化`INIParser`！

#### 读取单个文件
`read(inipath, errmsg="INI tree may not correct: ")`

比较安全的 INI 读操作，至少帮你捕获了`OSError`异常。  
若文件**成功读取**，则**返回`INIClass`文档实例**；
若**无法打开**，则用`errmsg`警告用户，并**返回`None`**。

> 实际上警告会先行输出`errmsg`，然后换行输出`OSError`的异常信息。

#### 序列读取 INI 文件组（或树）
`readTree(rootpath, *subpaths, sequential=False)`
    
**尝试**读取 INI 序列，或者深度优先（DFS）遍历 INI `[#include]`嵌套树，并将这些 INI 合并成一个`INIClass`文档实例。

> 这里说“尝试”是因为，有一些 INI 文件可能被打包进 Mix，或是经加密处理。这些**无法读取的 INI 文件，可能会影响到合并后 INI 文档的完整性**。

另外注意，其一，对于关键字`sequential`有两种情况：
- 若为`True`，则只读取`rootpath`和`subpaths`，不再处理每个文件里的`[#include]`；
- 若为`False`，则只遍历`rootpath`那棵嵌套树，不会接着读`subpaths`。

其二，DFS 遍历遵循“同源”假设——即要求所有 INI 均处于同一级父目录之下：
- 游戏根目录：`D:\AresYR\`
    - INI 树根节点：`rulesmd.ini`
    - 孩子节点：`rules_hotfix.ini`
    - 子文件夹：`INIs\`
        - 孩子节点：`rules_global.ini`
        - ...
    - ...

### 写方法
`write(doc, inipath, encoding='utf-8', *, pairing='=', blankline=1)`

将 INI 文档实例`doc`写回一个 INI 文件`inipath`。  
当然还有些关键字参数：

- `pairing`：控制键值对之间如何连接。

    默认`key=val`这么连接。你也可以改用`  =   `。
    当然`: `就算了，读方法不支持。

- `blankline`：控制两个小节之间如何换行。

    默认空 1 行：
    ```ini
    [a]
    blbla = cache
    
    [d]
    erotic = sese
    ```