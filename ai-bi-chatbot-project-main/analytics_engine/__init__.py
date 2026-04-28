"""Analytics Engine - Advanced Query Processing and KPI Analysis"""

try:
    from .core.engine import process_query
    from .insights.insight_generator import generate_insight
except ImportError:
    pass
