# 拆分与组合（用于 Git）

> 模块名：`map_split`  
> API 已在`pyalert2yr`包中直接提供。无需再导入模块。

地图作为文本文件，很适合用 Git 记录差异。相比起“复制、重命名”的日期备份，Git 可以更快更好地帮助你“回溯”，甚至定位问题所在。

然鹅，有些改动规模可以很大（新增小队、触发，上头了可以很快就加多一百来行）；而像地形这类经过压缩的文本，如同天书，用 Git 比较差异更是没有意义。

因此，有必要将地图拆分为小规模的子 ini 和二进制文件，并在必要时重组。

- `splitMap(iniclass_item, output_dir)`
将地图文件拆分成若干子文件，以便 Git 分辨差异。

> `iniclass_item`：INI 实例（或者说地图实例）  
> `output_dir`：导出文件夹路径  

- `joinMap(sources_dir, output_file_name)`
将拆分的地图合并为一个`.map`文件。合并后的地图文件**置于拆分目录之中**。

> `sources_dir`：源文件夹路径  
> `output_file_name`：导出文件名（后缀名固定`.map`）  
> 注：只合并因本工具而生的文件，不处理`[#includes]`。