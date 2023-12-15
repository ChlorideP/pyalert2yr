# 红红地图工具集

## Python 3

最低支持 [Python 3.8.10](https://www.python.org/downloads/release/python-3810/). 更低版本未经测试。  
点进去往下翻到 Files 部分，根据你的系统选择合适的安装包。安装过程恕不赘述。

## 安装依赖
在工具集根目录`Shift + F10`，打开“命令提示符”或“PowerShell”，并执行下列命令：
```cmd
pip install -r requirements.txt
```

> 您可能需要考虑换源（比如清华镜像），否则可能会下载失败。详情还请自行百度。

## 食用

基本上开袋即食。

唯一需要注意的是，你的工具集文件夹将**直接作为包名导入**。  
因此，最好先检查文件夹名称：
- **不能**以数字或下划线开头
- **不能**含有空格或其他特殊字符（除了下划线）
- 包名**区分大小写**。

```python
from py_yrmap_tools.ini import INIClass

if __name__ == '__main__':
    ccwc = INIClass()
    ccwc['fa2py3'] = {'version': 114514}
    with open('./version.ini', 'w', encoding='utf-8') as fp:
        ccwc.writeStream(fp)

```

## 可用功能一览

欢迎提交功能需求（

- [INI](https://github.com/ClLab-YR/py_yrmap_tools/blob/master/docs/ini.md)
- [用于 Git 的地图拆分与组合](https://github.com/ClLab-YR/py_yrmap_tools/blob/master/docs/export.md)
