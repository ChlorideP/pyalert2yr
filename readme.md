# 红红地图工具脚本库 - RA2 Map Script Lib

## Python 3

This script library is written on Python v3.8.10, which is the final version compatible with Windows 7.  
Before creating your own stuffs, you have to install it.  
最低支持 [Python 3.8.10](https://www.python.org/downloads/release/python-3810/). 更低版本未经测试。  
点进去往下翻到 Files 部分，根据你的系统选择合适的安装包。安装过程恕不赘述。

## 安装依赖 - Package Dependencies
In Windows, you could simply open your lib directory, start CMD or PowerShell with `Shift + F10` hotkey,
and execute the following command.  
在工具集根目录`Shift + F10`，打开“命令提示符”或“PowerShell”，并执行下列命令：
```cmd
pip install -r requirements.txt
```

> 您可能需要考虑换源（比如清华镜像），否则可能会下载失败。详情还请自行百度。

## 食用 - Usage
Unlike the common way (pip) to deploy the python package, this lib needs **manual downloading (or git cloning)**.  
In case, I would like to consider it just submodule, embedded in another git repository, like [RA2MapSplitTemplate](https://github.com/ClLab-YR/RA2MapSplitTemplate).  
基本上开袋即食。

As python would import package just by the directory name, you have to be careful with it.  
Basically, here are some tips when deciding Ur package name:  
唯一需要注意的是，你的工具集文件夹将**直接作为包名导入**。  
因此，最好先检查文件夹名称：
- MUST NOT begin with digits or `_`
- MUST NOT consists with special chars within ` `, except `_`
- It's case sensitive
- **不能**以数字或下划线开头
- **不能**含有空格或其他特殊字符（除了下划线）
- 包名**区分大小写**。

```python
from pyalert2yr.csf import importJSONV2

if __name__ == '__main__':
    ccwc = importJSONV2('~/ES/stringtable114514.json')
    ccwc['TXT_RELEASE_NOTE'] = {'value': 'Extreme Starry v0.6'}
    ccwc.writeCsf('~/ES/stringtable99.csf')
```

## 可用功能一览 - APIs

The following API documents are available in **Simplified Chinese only**.  
You may get English help by `help()` function.

欢迎提交功能需求（

- [INI](https://github.com/ClLab-YR/pyalert2yr/blob/master/docs/ini.md)
- [CSF](https://github.com/ClLab-YR/pyalert2yr/blob/master/docs/csf.md)
- [Split/Join MAP for git management - 用于 Git 的地图拆分与组合](https://github.com/ClLab-YR/pyalert2yr/blob/master/docs/export.md)
