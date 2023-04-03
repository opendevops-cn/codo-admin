#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/22 16:43 
Desc    : 解释一下吧
"""

from concurrent import futures
import grpc
import SimpleCal_pb2
import SimpleCal_pb2_grpc

class CalServicer(SimpleCal_pb2_grpc.CalServicer):
  def Add(self, request, context):   # Add函数的实现逻辑
    print("Add function called")
    return SimpleCal_pb2.ResultReply(number=request.number1 + request.number2)

  def Multiply(self, request, context):   # Multiply函数的实现逻辑
    print("Multiply service called")
    return SimpleCal_pb2.ResultReply(number=request.number1 * request.number2)

def serve():
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
  SimpleCal_pb2_grpc.add_CalServicer_to_server(CalServicer(),server)
  server.add_insecure_port("[::]:5005")
  server.start()
  print("grpc server start...")
  server.wait_for_termination()

if __name__ == '__main__':
  serve()