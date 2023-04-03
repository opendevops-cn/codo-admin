#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/22 16:44 
Desc    : 解释一下吧
"""
import SimpleCal_pb2
import SimpleCal_pb2_grpc
import grpc

def run(n, m):
  # channel = grpc.insecure_channel('localhost:50051') # 连接上gRPC服务端
  channel = grpc.insecure_channel('10.10.6.154:11000')  # 连接上gRPC服务端
  stub = SimpleCal_pb2_grpc.CalStub(channel)
  response = stub.Add(SimpleCal_pb2.AddRequest(number1=n, number2=m))  # 执行计算命令
  print(f"{n} + {m} = {response.number}")
  response = stub.Multiply(SimpleCal_pb2.MultiplyRequest(number1=n, number2=m))
  print(f"{n} * {m} = {response.number}")

if __name__ == "__main__":
  run(100, 300)