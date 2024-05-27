# Ares INI

> 模块名：`formats.ini`  
> 此模块全部 API 均可直接从`pyalert2yr`包中取用。

重写了一下读取，不过应该好不了多少。~~我好懒，文档都不想写。说真的有人用嘛？~~  
文档中对于 INI 的扩展语法和功能可参见`IniExt`库里的[部分介绍](https://github.com/ClLab-YR/Chloride.RA2Scripts/blob/master/IniExt.ReadMe.md)。

## INI 小节 `INISection`
继承自`MutableMapping`。现**接受注释的存储，但不允许用户直接访问注释**（这点与`IniExt`不同）。

你需要**自行注意值类型的转换**。比如游戏中读`bool`只看首字符，`1 t y`为`True`，`0 f n`为`False`。  
同样，原则上小节字典只接受`str`和`None`型，但 Python 运行时并没有特别的约束。

* `summary`字段：包含在节声明行里的注释（如`[GAPOWR]; Power Plant`）
- `INISection()`初始化：无参，实例化一个 INI 小节字典。**若需要修改`summary`字段，也应在初始化完成后进行**。
- `section[key]`下标访问：
    - get 操作只会取出该`key`对应的值，注释忽略；
    - set 操作也只会将值赋在下标 0 位置上，哪怕你试图传入`[val, desc]`这种列表。
- `keys()` `values()` `items()`序列捕获：将忽略所有的注释。

## INI 文档 `INIClass`
现继承自`MutableMapping`。

### 字段

* `header`：在 INI 文件开头的，匿名的虚拟小节。该小节里的内容在所有`[]`小节声明之前：
```ini
; blabla
key=val
[General]
ddtms=false
```
* `inheritance`：继承关系表
    - 继承关系原先位于小节定义中，现在由 INI 文档统一管理。
    - 实为形如`{ child: parent }`的字典。

### 方法

> ~~我知道这边都是无序列表堆料，但我真的好懒（）~~  
> ~~说到底我搞来搞去都是这些容器数据结构。咱能想起来的改进别人早都搓好了。~~  
> ~~唔 这么想来自己果然好废物啊。~~

- `INIClass()`初始化：无参，实例化一个 INI 字典。
- `del ini[section]`删除小节：会**连带剔除相应的继承关系**。
- `clear()`清空：会清空所有继承关系、开头匿名小节，以及小节字典。

* `getTypeList(section)`方法：获取某小节的**不重复、有序**值表。常用于红红的“注册表”。
* `recursiveFind(section_start, key)`方法：从某一小节开始，向亲代（父小节）查找对应键值。
    - 与继承关系一样，原先是小节里的方法。
    - 返回（所属小节，相应值）二元组。元组中的元素若为`None`，说明没有找到。
* `rename(old, new)`方法：允许对某一小节重命名。
    - 该小节在 INI 文件的相对位置不变，继承关系则会迁移。
    - 由于不再涉及`INISection`的同步更新，其`summary`字段可能仍需手动修改。

- `read(*ini_paths)`读方法：与旧版效果一致，但改为生产者—消费者模型。
    - `read()`方法现只负责创建文件句柄，**实际读取转到后台进行**。
    - **读取不再需要指定编码**了——现在会在读取过程中途猜测编码，猜错了也有`utf-8` `gbk`保底。
- `write(filename, encoding, pairing='=', commenting='; ', blankline=1)`写方法：
    - 与旧版`writeStream()`相比，省略了`open()`创建文件句柄的环节。
    - `pairing`参数控制键值对如何连接。默认`key=value`。
    - `commenting`参数控制**单独的**行注释如何开头。默认`; ssks`。  
    注意`key=value  ; comment`这种尾随注释不受参数影响。
    - `blankline`参数控制小节之间空多少行。默认 1 行。
    - 实际上变得不多（）主要是因为设计上的变动，相应地有所调整。

## INI 嵌套树深度优先遍历 `iniTreeDFSWalk`

> 原理参见 Ares 的 [#include](https://ares-developers.github.io/Ares-docs/new/misc/include.html?highlight=include) 文档。~~实际上就是树的先序遍历（~~

`iniTreeDFSWalk(root_ini_filepath)`可以为你获取较为完整的 INI 遍历序列，其中第一个元素为根 INI 本身。但需要注意，该函数基于以下两点假设：

- 根 INI 与子 INI **在同一级目录下**：
```
- c&c2yuri (dir)
    - rulesMD.ini (root INI)
    - rules_hotfix.ini (sub INI: placed together)
    - INI (dir)
        - rules_Generic.ini (sub INI: sub directory)
        - ...
```
- 所有 INI **均可读**（未被打包在 MIX 里，未被加密）。~~而 Ares 不用考虑这条（~~

此外，尽管 INI 读取改用了生产者—消费者模型，但只读一个 INI 文件的时间开销并没有变化。  
不幸的是，DFS 必须先等待当前根节点 INI 读完，才能获取下一级的`#include`。换言之，优化了吗？如优。
