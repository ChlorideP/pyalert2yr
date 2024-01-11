# 红红语言文件 `.CSF` 支持库

> 模块名：`csf`  
> CSF 文件逻辑上看，就是个**连续存储**的字典。

提供 CSF 文件的读取、存储，以及与 JSON XML 的相互转换。  
转换出来的 JSON 遵循 [ShimakazeProject](https://github.com/ShimakazeProject) 编写的语义规范，XML 则部分遵循。

```python
>>> import pyalert2yr.csf as csf
>>> csf.__all__
['CSF_TAG', 'LBL_TAG', 'VAL_TAG', 'EVAL_TAG', 'LANG_LIST',
 'CsfHead', 'CsfVal', 'CsfDocument', 'InvalidCsfException',
 'csfToJSONV2', 'csfToXML', 'importJSONV2', 'importXML']
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
        注：多值标签游戏里只会读第一个值。"""
    def __delitem__(self, label: str):
    def __iter__(self):
        """标签—值字典的迭代器"""
    def __len__(self):
        """标签总数"""
    @property
    def header(self) -> CsfHead:
        """返回最新的 CSF 首部信息"""
    def setdefault(self, label, string, *, extra=None):
        """若文档中不存在指定标签，则追加指定键值"""
    def readCsf(self, filepath):
        """读入 CSF 文件（无需手动 open() 开辟缓冲区）"""
    def writeCsf(self, filepath):
        """输出 CSF 文件（无需手动 open() 开辟缓冲区）"""
```

### 格式转换：`csfToX` `importX`

- `csfToJSONV2(csf_doc, jsonpath, encoding='utf-8', indent=2)`：
将 CSF 另存为 Shimakaze JSON V2 格式。
- `importJSONV2(jsonpath, encoding='utf-8')`：
初始化 CSF，并导入指定 JSON 文件。

* `csfToXML(csf_doc, xmlpath, encoding='utf-8', indent='\t')`：
将 CSF 另存为 XML 文档。
* `importXML(xmlpath)`：
初始化 CSF，并导入指定 XML 文档。

## 常量

### 标识符 
共四个：`CSF_TAG` `LBL_TAG` `VAL_TAG` `EVAL_TAG`  
用于验证 CSF 文件合法性。

> 根据 ModEnc：
> - 若文件头`CSF_TAG = " FSC"`校验失败，游戏直接跳过不读；
> - 若标签首部`LBL_TAG = " LBL"`校验失败，游戏会忽略该标签，并尝试读接下来的 4B；我比较懒，失败了直接抛异常。
> - 若值首部检验失败，不是`VAL_TAG = " RTS"`，也不是`EVAL_TAG = "WRTS"`，则记录非法，我选择抛异常。

### 可选语言 `LANG_LIST`
实际上 CSF 是支持多语言的。`CsfDocument`中的语言 ID 对应列表的下标。  
列表按顺序列示如下。部分我知道的语言给出了中文对照。红红官方发行的语言用**粗体**表示。

- **en_US  英语-美国**
- en_UK  英语-英国
- **de    德语**
- **fr    法语**
- es    西班牙语
- it    意大利语
- jp    日语
- Jabberwockie
- **kr    韩语**
- **zh    中文**

说实话改这个意义也不大。目前流通的 CSF 文件语言 ID 都是 0，即`en_US`（英语-美国）。  
可能原本是有多语言文本并存的打算吧。

## 其他

### CSF 首部：`CsfHead`

对应`.csf`文件的前 0x18 字节。目前仅用于`.csf`文件的读写。  
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

~~其实有想过给语言整个枚举类型，但是没什么必要。~~

## Bibliography（雾）
1. Anonymous. [CSF File Format](https://modenc.renegadeprojects.com/CSF_File_Format). ModEnc. 2021.
2. Frg2089. [Shimakaze's schemas](https://github.com/ShimakazeProject/Schemas). ShimakazeProject.
3. Frg2089. [Shimakaze.Tools](https://github.com/ShimakazeProject/Shimakaze.Tools). ShimakazeProject.
