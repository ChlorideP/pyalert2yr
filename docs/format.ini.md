# Ares INI

> 模块名：`formats.ini`  
> 此模块全部 API 均可直接从`pyalert2yr`包中取用。

重写了一下读取，不过应该好不了多少。~~我好懒，文档都不想写。说真的有人用嘛？~~

## INI 小节 `INISection`
现直接继承自`dict`，并且也**接受注释的存储**（和`Chloride.RA2Scripts`一样）。

> 你需要**自行注意值类型的转换**。比如游戏中读`bool`只看首字符，`1 t y`为`True`，`0 f n`为`False`，显然`yno`也是`True`。  
> 同样，原则上小节字典只接受`str`和`None`型，但 Python 运行时并没有特别的约束。

* `summary`字段：包含在节声明行里的注释（如`[GAPOWR]; Power Plant`）
- `INISection()`初始化：与`dict`类似，但很可惜没有`{}`那么轻便。若需要修改`summary`字段，也应在初始化完成后进行。
- `section[key]`下标访问：
    - get 操作只会取出该`key`对应的值，注释忽略；
    - set 操作也只会将值赋在对应位置上，哪怕你试图传入`[val, desc]`这种带注释的值列表。
- 单独行注释：运行时以`{ ';a8a8a8a8': [None, "ddtms"] }`这种形式存储。键部分为 UUID 前 8 位。

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
* `inheritance`：
    - 继承关系原先位于小节定义中，现在由 INI 文档统一管理。
    - 实为形如`{ child: parent }`的字典。

### 方法

> ~~我知道这边都是无序列表堆料，但我真的好懒（）~~  
> ~~说到底我搞来搞去都是这些容器数据结构。咱能想起来的改进别人早都搓好了。~~  
> ~~唔 这么想来自己果然好废物啊。~~

- `INIClass()`初始化：无参，实例化一个 INI 字典。
- `del ini[section]`删除小节：会**连带剔除相应的继承关系**。
- `clear()`清空：会清空所有继承关系、开头匿名小节，以及小节字典。

- `read(*ini_paths)`读方法：与旧版效果一致，但改为生产者—消费者模型。
    - **读取不再需要指定编码**了——`chardet`库将负责主要的编码~~竞猜~~分析  
    编码竞猜有置信度，相应地会歪保底。小保底`utf-8`，大保底`gbk`，保底不考虑偏门编码，如`shift-JIS`
    - `read()`方法现只负责创建文件句柄，**实际读取转到后台进行**。

- `write(filename, encoding, pairing='=', commenting='; ', blankline=1)`写方法：
    - 与旧版`writeStream()`相比，省略了`open()`创建文件句柄的环节。
    - `pairing`参数控制键值对如何连接。默认`key=value`。
    - `commenting`参数控制**单独的**行注释如何开头。默认`; ssks`。  
    注意`key=value  ; comment`这种尾随注释不受参数影响。
    - `blankline`参数控制小节之间空多少行。默认 1 行。
    - 实际上变得不多（）主要是因为设计上的变动，相应地有所调整。

* `getTypeList(section)`方法：获取某小节的**不重复、有序**值表。常用于红红的“注册表”：
```ini
[InfantryTypes]
; just consider it abstract class, and these values are "instances" of it.
0=CHLORIDEP
1=MELOLAND
+=SECSOME
+=THOMAS_SNEDDON
```
* `recursiveFind(section_start, key)`方法：从某一小节开始，向亲代（父小节）查找对应键值。
    - 与继承关系一样，原先是小节里的方法。
    - 返回（所属小节，相应值）二元组。元组中的元素若为`None`，说明没有找到。
* `rename(old, new)`方法：允许对某一小节重命名。
    - 该小节在 INI 文件的相对位置不变，继承关系则会迁移。
    - 由于不再涉及`INISection`的同步更新，其`summary`字段可能仍需手动修改。

## INI 嵌套树先序遍历 `scanINITree`

结合 Ares 对 [#include](https://ares-developers.github.io/Ares-docs/new/misc/include.html?highlight=include) 的说明和数据结构的姿势，易得 Ares 做的先序遍历。那么我们也这么读就是了。

> 原文翻译：  
> 在 `[#include]` 中包含的子 INI 会在**根 INI 读完之后马上读取**。子 INI 也**可以再下设** `[#include]` 读取更多拆分的 INI。该嵌套没有层级限制，并且**遵循深度优先**读取。  
> 举例：`a -> b -> c, d`。在 c 读完之后会再读 d，完事之后再回到 b 那一级。如果还有套娃那就接着剥衣服。

> ~~实际上 INI 文件树只有一个根节点（Rules 和 Art 显然事两棵不同的树），所以实际上对其深度优先就是先序（上面那个例子正好是个二叉树，b-c-d，根-左-右）。~~

`scanINITree(root_ini_filepath)`可以为你获取较为完整的 INI 遍历序列，其中第一个元素为根 INI 本身。

但需要注意，该函数有两点假设作为前提：

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
