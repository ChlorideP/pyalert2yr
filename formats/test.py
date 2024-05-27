# -*- encoding: utf-8 -*-
# @File   : test.py
# @Time   : 2024/05/27 22:06:25
# @Author : Chloride

import ini

eg = ini.INIClass()
eg.readTree('/home/chloridep/Desktop/ES-Global-configs/ruleses.ini')
eg.clear()
eg.readTree('/home/chloridep/Desktop/ES-Global-configs/artes.ini')
eg.clear()
