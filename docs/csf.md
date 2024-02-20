# 红红语言文件 `.CSF` 支持库

> 模块名：`csf`  
> CSF 类可直接从包中取用。除 JSON 外，其余的格式转换 API 仍需显式导入。

提供 CSF 文件的读取、存储，以及与 JSON XML YAML 的相互转换。  
转换出来的 JSON 和 XML 遵循 [ShimakazeProject](https://github.com/ShimakazeProject) 编写的语义规范。  
YAML 则简化处理，尽管也遵循上述规范，但只接受纯文本键值对。

> 有条件的可以考虑 [Shimakaze.Sdk](#bibliography雾)。~~别的不说，至少他的 CSF 工具可以完美兼容我导出的 YAML 文档，反之就不一定了。~~  

```python
>>> import pyalert2yr.csf as csf
>>> csf.__all__
['CSF_TAG', 'LBL_TAG', 'VAL_TAG', 'EVAL_TAG',
 'CsfHead', 'CsfLang', 'CsfVal', 'CsfDocument',
 'InvalidCsfException', 'EditorIncompatibleWarning',
 'csfToJSONV2', 'csfToXMLV1', 'importJSONV2', 'importXMLV1',
 'csfToSimpleYAML', 'importSimpleYAML']
```

## 可食用 API

### CSF 值结构：`CsfVal`
本质上是固定框架的字典：
```python
class CsfVal(TypedDict):
    value: Union[str, List[str]]
    extra: Optional[str]
```
要声明一个值类型，至少需要填入`value`字段。  
如果是用*带有 Python 检查*的编辑器，有可能会提示你缺失`extra`字段。用`None`补上即可。
> 原版`ra2md.csf`里涉及到`extra`字段的只有`VOX:xxxx`，对应 EVA 语音、人物台词的翻译。

**在`CsfDocument`里，`value`字段一定是`str`类型。** 用户为 CSF 实例增、改值时应加以注意。

> 声明中带上`List[str]`是为了 JSON 转换用，  
> Shimakaze's schema 要求多行字符串须按`\n`分割成字符串数组。

### CSF 文档类：`CsfDocument`
```python
class CsfDocument(MutableMapping):
    version = 3  # CSF 版本（RA2 YR 均为 3）
    language = 0  # 语言 ID，即 LANG_LIST 对应元素的下标。

    def __init__(self):
    def __getitem__(self, label: str) -> CsfVal | List[CsfVal]:
        """多值标签返回整个列表；
        单值标签只返回第一个（相当于帮你省去 [0] 下标访问）"""
    def __setitem__(self, label: str, val: CsfVal | List[CsfVal]):
        """传入列表：直接覆盖。传入单个 CsfVal：覆盖 [0] 号位。
        注意：游戏只会读第一个值。红警风暴语言编辑器也只能读出两个值。"""
    def __delitem__(self, label: str):
    def __iter__(self):
        """标签—值字典的迭代器"""
    def __len__(self):
        """标签总数"""
    @property
    def header(self) -> CsfHead:
        """返回最新的 CSF 首部信息"""
    def getValidValue(self, label) -> Optional[str]:
        """返回游戏实际读取的键值。"""
    def setdefault(self, label, string, *, extra=None):
        """若文档中不存在指定标签，则追加指定键值"""
    def readCsf(self, filepath):
        """读入 CSF 文件（无需手动 open() 开辟缓冲区）"""
    def writeCsf(self, filepath):
        """输出 CSF 文件（无需手动 open() 开辟缓冲区）"""
```

### 格式转换：`csfToX` `importX`

下列函数无需再配合`open()`开辟的缓冲区食用了。

- `csfToJSONV2(csf_doc, jsonpath, encoding='utf-8', indent=2)`：
将 CSF 另存为 Shimakaze JSON V2 格式。
> `csf_doc`: `CsfDocument` 实例  
> `jsonpath`: JSON 文件路径  
> `encoding`: 编码  
> `indent`: 每个块缩进多少空格  

- `importJSONV2(jsonpath, encoding='utf-8')`：
初始化 CSF，并导入指定 JSON 文件。
> `jsonpath`: JSON 文件路径  
> `encoding`: 编码

* `csfToXMLV1(csf_doc, xmlpath, indent='\t')`：
将 CSF 另存为 Shimakaze XML V1 文档。  
> `csf_doc`: `CsfDocument` 实例  
> `xmlpath`: XML 文档路径  
> `indent`: 如何缩进（默认一个 Tab 键）

> 由于 XML 的编码定义不多，为避免意外，统一采用`utf-8`编码。

* `importXMLV1(xmlpath)`：
初始化 CSF，并导入指定 XML 文档。
> `xmlpath`: XML 文档路径

- `csfToSimpleYAML(csf_doc, yamlpath, encoding='utf-8', indent=2)`：
将 CSF 另存为简化 YAML 文档。
> `csf_doc`: `CsfDocument` 实例  
> `yamlpath`: YAML 文件路径  
> `encoding`: 编码  
> `indent`: 每个块缩进多少空格

> 注意：只会保存游戏实际显示的值字符串，
> - 若标签对应多个值，只取第一个；
> - 若第一个值存在额外记录`extra`，忽略该记录。

- `importSimpleYAML(yamlpath, encoding='utf-8')`：
初始化 CSF，并导入简化 YAML 文档。
> `yamlpath`: YAML 文件路径  
> `encoding`: 编码

> 注意：尽可能只传入本模块导出的简化 YAML，`Shimakaze.Sdk.Csf.Converter`导出的 YAML 有可能报错！

## 寄术细节

关于`.csf`文件详细的读写脉络可以参看源代码和 ModEnc，恕不赘述。

### 标识符 
共四个：`CSF_TAG` `LBL_TAG` `VAL_TAG` `EVAL_TAG`  
用于验证 CSF 文件合法性。

> 根据 ModEnc：
> - 若文件头`CSF_TAG = " FSC"`校验失败，游戏直接跳过不读；
> - 若标签首部`LBL_TAG = " LBL"`校验失败，游戏会忽略该标签，并尝试读接下来的 4B；我比较懒，失败了直接抛异常。
> - 若值首部检验失败，不是`VAL_TAG = " RTS"`，也不是`EVAL_TAG = "WRTS"`，则记录非法，我选择抛异常。

### 可选语言
实际上 CSF 是支持多语言的。`CsfDocument`中的语言 ID 对应下列语言的序号。  
部分我知道的语言给出了中文对照。红红官方发行的语言用**粗体**表示。

0. **en_US  英语-美国**
1. en_UK  英语-英国
2. **de    德语**
3. **fr    法语**
4. es    西班牙语
5. it    意大利语
6. jp    日语
7. Jabberwockie
8. **kr    韩语**
9. **zh    中文**

上表在源代码中以枚举类`CsfLang`体现。~~当然实际上并没有用到。~~  
Ares 另外引入了`-1`作为通用语，意指这个 CSF 文件兼容上述所有语言。

说实话改这个意义也不大。目前流通的 CSF 文件语言 ID 都是 0，即`en_US`（英语-美国）。  
可能原本是有多语言文本并存的打算吧。

### CSF 首部

`CsfHead`类对应`.csf`文件的前 0x18 字节。目前仅用于该文件类型的读写。  
**一经初始化即只读**。

```python
class CsfHead(NamedTuple):
    # validate: str  # char[4]  # 0x00
    version: int  # unsigned long => DWORD  # 0x04
    numlabels: int  # DWORD     # 0x08
    numvalues: int  # DWORD     # 0x0C
    unused: int     # DWORD     # 0x10
    language: int   # DWORD     # 0x14
```

## 后记

做地图免不了要~~跟文案打交~~写任务文本嘛。说实话也是为了自己干活方便。  

[Zero Fanker](https://github.com/Zero-Fanker)算是最早开始在红警 MOD 这里大规模应用 Git 的案例了，
[岛风酱](https://github.com/frg2089)也力荐把地图用 Git 管理起来，后来我也这么做了。  

CSF 本是二进制，但究其本质也不过是个字典。于是岛风干脆考虑把它转化成文本文件，于是`Shimakaze.Utils.Csf`出现了。  
在数次迭代之后，岛风终于发现，现有的工具集是有极限的，全力去搞他的 RA2 MOD SDK 去了。  

我是没有做 mod 那种抱负，做地图需要打交道的组件也不多（大概？），
所以还是决定另立门户，用 Python 实现一个，然后集成进我负责的地图项目里面。~~至少只剩 FA2 或者船新地编需要下崽辣。~~

目前就这样罢。以后的事留给以后的我操心好了。~~希望那时的我没事（笑）~~

## Bibliography（雾）
1. Anonymous. [CSF File Format](https://modenc.renegadeprojects.com/CSF_File_Format). ModEnc. 2021.
2. Frg2089. [Shimakaze's schemas](https://github.com/ShimakazeProject/Schemas). ShimakazeProject.
3. Frg2089. [Shimakaze.Sdk](https://github.com/ShimakazeProject/Shimakaze.Sdk). ShimakazeProject.
