# 用例 - Usage

> I got lazy to translate them, so the explanation would be available ONLY in Simplified Chinese.  
> Or, you may be able to **guess** what the codes below are doing, by each **title**.

这里提供一些我觉得有点实用性，但是暂时做不到泛用性的脚本用例。

## 猹询 CSF 缺失 - Check out Missing CSF in Map
猹询地图里引用的，CSF 里却没有的词条。  
暂时只考虑单 CSF 和原版触发情形。
```python
from pyalert2yr.formats import ini, csf

# actions format:
# TriggerID = ActionsCount, (a1_id,p1,p2,p3,p4,p5,p6,p7), ...
text_trigger_actions = ['11', '103']

mp = ini.INIClass()
mp.read(input("MAP FILE PATH: "))
lang = csf.CsfFileParser(input("CSF FILE PATH: ")).read()

for i, j in mp['Actions'].items():
    j = j.split(',')
    length = int(j[0])
    lbl = mp['Triggers'][i].split(',')[2]

    k = 1
    for _ in range(length):
        curaction = j[k:k+9]
        if (curaction[0] in text_trigger_actions and
                curaction[2] not in lang):
            print("Found missing csf '{}' in {} {}".format(
                curaction[2], i, lbl))
        k += 8
```
