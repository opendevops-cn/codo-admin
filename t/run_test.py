#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/6/1 15:33 
Desc    : 解释一下吧
"""
import unittest
from .storage_test import TestStorageApp

class A(unittest.TestCase):

    def test_case(self):
        self.assertTrue(1)


class DemoTest(unittest.TestCase):

    def test_pass(self):
        self.assertTrue(True)

    def test_fail(self):
        self.assertTrue(False)

