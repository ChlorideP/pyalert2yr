# Ares INI

该模块本身不作为工具对外提供，但仍向包提供了**基于 Ares 的无注释** INI 实现。  
~~也算是 PyMapRA2 的遗产（现在看来实在太臃肿了，用起来也麻烦）。可惜旧文档已经找不到了，我也懒得重新写一份。用 IDE 的英文注解将就下算了（~~

- `INISection` INI 小节类
- `INIClass` INI 文档类
- `scanIncludes(ini_root_path)`
搜索`[#includes]`子 INI，并**尽可能**按游戏读取的顺序排列。

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