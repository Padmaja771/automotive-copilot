import logging

logger = logging.getLogger("AI_Metrics")

def record_metric(metric_name: str, value: float, tags: dict = None):
    """Simulates sending an isolated gauge metric to Datadog / Prometheus"""
    tag_str = ", ".join([f"{k}:{v}" for k, v in (tags or {}).items()])
    logger.info(f"📈 [METRIC] {metric_name} = {value:.3f} | Tags: [{tag_str}]")
