import os
import json
import re
from typing import Dict, Any

class ChatbotService:
    """Handle chatbot queries and answers using Gemini API and rule-based engine"""
    
    def __init__(self, gemini_api_key=None):
        """Initialize chatbot with optional Gemini API key"""
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')
        self.data_context = None  # Will store user's data context
        
        # Predefined question templates
        self.predefined_questions = {
            "top_customers": {
                "question": "Who are my top customers?",
                "intent": "find_top_customers",
                "requires_data": True
            },
            "revenue_trend": {
                "question": "What's my revenue trend this month?",
                "intent": "revenue_analysis",
                "requires_data": True
            },
            "at_risk": {
                "question": "Which customers are at risk?",
                "intent": "churn_analysis",
                "requires_data": True
            },
            "top_product": {
                "question": "Which product category sells most?",
                "intent": "product_analysis",
                "requires_data": True
            },
            "sales_forecast": {
                "question": "What will my sales be next month?",
                "intent": "forecast_query",
                "requires_data": True
            },
            "growth_strategy": {
                "question": "How can I increase revenue?",
                "intent": "strategic_advice",
                "requires_data": True
            }
        }
    
    def set_data_context(self, data_context: Dict[str, Any]):
        """Set the user's data context for personalized responses"""
        self.data_context = data_context

    def _as_float(self, value, default=0.0) -> float:
        """Convert possibly-missing numeric values to float safely."""
        try:
            if value is None:
                return float(default)
            return float(value)
        except Exception:
            return float(default)
    
    def get_predefined_questions(self):
        """Return list of predefined questions"""
        return [q['question'] for q in self.predefined_questions.values()]
    
    def process_question(self, question: str, use_gemini: bool = False):
        """
        Process user question and return answer
        
        Args:
            question: User's question string
            use_gemini: Whether to use Gemini API (if configured)
        
        Returns:
            Dict with answer, confidence, and metadata
        """
        
        if not self.data_context:
            return {
                'success': False,
                'answer': 'Please upload your data first to ask questions.',
                'confidence': 0.0,
                'source': 'system'
            }
        
        # Check if it's a predefined question
        matched_question = self._match_predefined_question(question)
        
        if matched_question:
            answer = self._answer_predefined_question(matched_question)
            return {
                'success': True,
                'answer': answer,
                'confidence': 0.95,
                'source': 'predefined',
                'question_type': matched_question['intent']
            }
        
        # Try to answer using data analysis
        datadriven_answer = self._analyze_question(question)
        if datadriven_answer:
            return {
                'success': True,
                'answer': datadriven_answer,
                'confidence': 0.8,
                'source': 'data_analysis',
                'question_type': 'custom'
            }
        
        # If Gemini is configured and enabled, use it for custom questions
        if use_gemini and self.gemini_api_key:
            try:
                gemini_answer = self._query_gemini(question)
                return {
                    'success': True,
                    'answer': gemini_answer,
                    'confidence': 0.75,
                    'source': 'gemini',
                    'question_type': 'custom'
                }
            except Exception as e:
                print(f"Gemini API error: {e}")
        
        # Fallback response
        return {
            'success': False,
            'answer': f"I couldn't understand your question. Try asking about: {', '.join(list(self.predefined_questions.keys())[:3])}",
            'confidence': 0.3,
            'source': 'fallback'
        }
    
    def _match_predefined_question(self, question: str):
        """Find matching predefined question"""
        question_lower = question.lower()
        
        for key, pq in self.predefined_questions.items():
            # Simple keyword matching
            if self._similarity_score(question_lower, pq['question'].lower()) > 0.6:
                return pq
        
        return None
    
    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings"""
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 and not words2:
            return 1.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0
    
    def _answer_predefined_question(self, pq: Dict[str, Any]) -> str:
        """Generate answer for predefined question"""
        intent = pq['intent']
        
        if intent == 'find_top_customers':
            return self._answer_top_customers()
        elif intent == 'revenue_analysis':
            return self._answer_revenue_trend()
        elif intent == 'churn_analysis':
            return self._answer_at_risk()
        elif intent == 'product_analysis':
            return self._answer_top_product()
        elif intent == 'forecast_query':
            return self._answer_sales_forecast()
        elif intent == 'strategic_advice':
            return self._answer_growth_strategy()
        
        return "I couldn't generate an answer for this question."
    
    def _answer_top_customers(self) -> str:
        """Answer about top customers"""
        if not self.data_context or 'business_snapshot' not in self.data_context:
            return "No data available."
        
        segments = self.data_context.get('segments', {})
        
        if not segments:
            return "Unable to identify top customers."
        
        response = "📊 **Your Top Customer Segments:**\n\n"
        
        rendered = 0
        for segment, info in segments.items():
            if not isinstance(info, dict):
                continue
            response += f"• **{segment}**: {int(info.get('count', 0))} customers\n"
            response += f"  - Average Spend: ${self._as_float(info.get('avg_monetary')):.2f}\n"
            response += f"  - Total Revenue: ${self._as_float(info.get('total_revenue')):.2f}\n\n"
            rendered += 1

        if rendered == 0:
            return "No segment-level customer details are currently available for this dataset."
        
        return response
    
    def _answer_revenue_trend(self) -> str:
        """Answer about revenue trends"""
        snapshot = self.data_context.get('business_snapshot', {})
        
        response = "📈 **Your Revenue Metrics:**\n\n"
        response += f"• **Total Revenue**: ${self._as_float(snapshot.get('total_revenue')):,.2f}\n"
        response += f"• **Average Order Value**: ${self._as_float(snapshot.get('average_order_value', snapshot.get('avg_order_value'))):.2f}\n"
        response += f"• **Total Orders**: {int(self._as_float(snapshot.get('total_orders'), 0))}\n"
        response += f"• **Unique Customers**: {int(self._as_float(snapshot.get('unique_customers'), 0))}\n"
        
        return response
    
    def _answer_at_risk(self) -> str:
        """Answer about at-risk customers"""
        churn = self.data_context.get('churn', {})
        
        if not churn.get('success'):
            return "Unable to analyze churn risk at this moment."
        
        response = "⚠️ **At-Risk Customer Analysis:**\n\n"
        response += f"• **Customers at Risk**: {churn.get('at_risk_count', 0)}\n"
        response += f"• **Revenue at Risk**: ${churn.get('revenue_at_risk', 0):,.2f}\n"
        response += "\n**Recommendation**: Implement targeted retention campaigns for high-value at-risk customers.\n"
        
        return response
    
    def _answer_top_product(self) -> str:
        """Answer about top products"""
        response = "🛍️ **Top Product Category:**\n\n"
        response += "Your product performance analysis shows key revenue drivers.\n"
        response += "Focus on scaling the top-performing categories through marketing and inventory optimization.\n"
        
        return response
    
    def _answer_sales_forecast(self) -> str:
        """Answer about sales forecast"""
        forecast = self.data_context.get('forecast', {})
        
        if not forecast.get('success'):
            return "Forecast data not available."
        
        response = "📅 **Sales Forecast (Next 4 Weeks):**\n\n"
        for item in forecast.get('forecast', [])[:4]:
            response += f"• **Week {item['week']}**: ${item['forecast']:,.2f}\n"
        
        return response
    
    def _answer_growth_strategy(self) -> str:
        """Provide growth recommendations"""
        response = "💡 **Strategic Growth Recommendations:**\n\n"
        response += "1. **Customer Retention**: Focus on your at-risk segments with loyalty programs\n"
        response += "2. **Product Focus**: Concentrate marketing on your top-performing categories\n"
        response += "3. **Inventory Planning**: Use forecasts to optimize stock levels\n"
        response += "4. **Segmentation**: Create segment-specific marketing campaigns\n"
        response += "5. **Seasonal Insights**: Adjust strategies based on seasonal trends\n"
        
        return response
    
    def _analyze_question(self, question: str) -> str:
        """Try to answer using data analysis"""
        question_lower = question.lower()
        
        # Revenue-related
        if any(word in question_lower for word in ['revenue', 'sales', 'money', 'earn']):
            return self._answer_revenue_trend()
        
        # Product-related
        if any(word in question_lower for word in ['product', 'category', 'item', 'merchandise']):
            return self._answer_top_product()
        
        # Customer-related
        if any(word in question_lower for word in ['customer', 'client', 'buyer']):
            return self._answer_top_customers()
        
        # Risk/Churn-related
        if any(word in question_lower for word in ['risk', 'churn', 'leave', 'lose']):
            return self._answer_at_risk()
        
        # Growth/Strategy-related
        if any(word in question_lower for word in ['growth', 'increase', 'strategy', 'recommend']):
            return self._answer_growth_strategy()
        
        return None
    
    def _query_gemini(self, question: str) -> str:
        """Query Google Gemini API for answer"""
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            # Create context-aware prompt
            context = f"""
You are a business analytics expert. The user has the following business data:
- Total Revenue: ${self._as_float(self.data_context.get('business_snapshot', {}).get('total_revenue')):,.2f}
- Average Order Value: ${self._as_float(self.data_context.get('business_snapshot', {}).get('average_order_value', self.data_context.get('business_snapshot', {}).get('avg_order_value'))):.2f}
- Unique Customers: {int(self._as_float(self.data_context.get('business_snapshot', {}).get('unique_customers'), 0))}

Answer the following question based on this context:
{question}

Provide a concise, actionable answer.
"""
            
            response = model.generate_content(context)
            return response.text
        
        except ImportError:
            raise Exception("google-generativeai library not installed")
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
