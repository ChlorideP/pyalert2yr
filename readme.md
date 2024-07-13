# 红红地图工具脚本库 - RA2 Map Script Lib

> [!note]
> 项目现在根据分支分成了两个版本：  
> `master`分支是 V1 版本，承载旧式的 Section Proxy 风格 INI 实现。  
> 由于我的地图模板，以及我正在维护的地图项目均是 V1 版本，因此这个分支自然没有放弃的理由（强行跟进会有一堆兼容性问题，算了罢）  
> `develop`分支是 V2 版本，采用 Thread Pool 试图追求更快的 INI 读取。  
> 这一版还没有经过严谨的测试，姑且先不合入主分支。但`Chloride.RA2Scripts`的 C# 脚本会逐步迁移至此，或许会有更多轮子也说不定。

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
In case, I would like to consider it just submodule, embedded in another git repository, like [RA2YRMapSplitTemplate](https://github.com/ClLab-YR/RA2YRMapSplitTemplate).  
基本上开袋即食。

As python would import package just by the directory name, you have to be careful with it.  
Basically, here are some tips when deciding Ur package name:  
唯一需要注意的是，你的工具集文件夹将**直接作为包名导入**。  
因此，最好先检查文件夹名称：
- MUST NOT begin with digits or `_`  
  **不能**以数字或下划线开头
- MUST NOT consists with special chars within ` `, except `_`  
  **不能**含有空格或其他特殊字符（除了下划线）
- It's case sensitive  
  包名**区分大小写**。

[More Usage - 更多用例](docs/samples.md)  
你也可以看看 [INI 实现](docs/format.ini.md)和 [CSF 实现](docs/format.csf.md)的详细解说，说不定会为你编写脚本提供帮助。  
目前来说，借助[MAP 地图文件的拆合脚本](docs/map_split.md)，我成功搭建起了`RA2YRMapSplitTemplate`，作为管理地图项目的仓库模板。

## 贡献 - Contribution

> [!important]
> 此项目即日起不再接受**来自本人**的 Pull Requests。对说的就是我自己，ChlorideP，Force Push 仙人。  
> 在 [Pr#10](https://github.com/ClLab-YR/pyalert2yr/pull/10) 玩脱之后，我还是回归本心——自己的项目随便自己作了。
> 
> 如果有意向贡献代码的大佬们**还请谨慎考虑开启 PR**。~~不过我想也没人愿意光顾我的垃圾站吧。~~  
> ~~毕竟你 ChlorideP 就是这么又菜又爱玩。什么都想会点，又什么都没学成。~~
