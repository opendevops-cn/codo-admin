#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2025/02/08 15:14
Desc    : 链路追踪
"""

import logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.tornado import TornadoInstrumentor
from websdk2.configs import configs
from websdk2.consts import const


def check_required_config():
    """
    检查是否所有必须的配置项都存在
    """
    tracing_service_name = configs.get(const.APP_NAME)
    jaeger_host = configs.get(const.JAEGER_EXPORTER_HOST)
    jaeger_port = configs.get(const.JAEGER_EXPORTER_PORT)

    # 检查配置项
    if not tracing_service_name:
        logging.error("服务名称未配置 (app_name)。")
        return False
    if not jaeger_host or not jaeger_port:
        logging.error("Jaeger Exporter 主机或端口未配置 (jaeger_exporter_host, jaeger_exporter_port)。")
        return False

    return True


def configure_jaeger_tracing():
    # 获取并设置服务名称
    tracing_service_name = configs.get(const.APP_NAME)
    resource = Resource(attributes={"service.name": tracing_service_name})

    # 创建 TracerProvider 实例并设置
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    logging.info(f"OpenTelemetry TracerProvider 已设置，服务名称: {tracing_service_name}")

    # 获取 Jaeger 配置并创建导出器
    jaeger_host = configs.get(const.JAEGER_EXPORTER_HOST)
    jaeger_port = configs.get(const.JAEGER_EXPORTER_PORT)

    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port
    )

    # 注册 Jaeger Exporter 并使用批处理 Span 处理器
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    logging.info(f"Jaeger Exporter 配置完成，主机: {jaeger_host}, 端口: {jaeger_port}")


def initialize_opentelemetry():
    if configs.get(const.OTEL_ENABLED) != "yes":
        return

    # 检查必需的配置项是否存在
    if not check_required_config():
        logging.error("配置不完整，无法启动 OpenTelemetry 链路追踪。")
        return

    # 配置 OpenTelemetry
    configure_jaeger_tracing()

    # 启用 Tornado 链路追踪
    TornadoInstrumentor().instrument()
    logging.info("CODO Tornado 链路追踪已启用。")
